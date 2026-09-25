# -*- coding: utf-8 -*-
"""
NOME: filesystem_item_publisher.py
TITULO: Adapter de ItemPublisher — publica itens do acervo em <projeto>/.claude/<tipo>s/
DATA: 25/09/2026 13:18
MODIFICADO: 25/09/2026 13:18
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports, praxisforge.domain
HISTÓRICO:
    - 25/09/2026 13:18: criação (T037, feature 009) — sucede filesystem_skill_publisher.py; lê o
      marcador da 008 e reconhece symlinks antigos para skills/
STATUS: DEV
"""

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from praxisforge.application.ports import ContractValidator, ItemPublisher, PublishedState
from praxisforge.domain.errors import (
    ForeignSkillDestinationError,
    PraxisForgeError,
    SkillPublicationError,
)
from praxisforge.domain.library_item import ItemKind

SKILL_MARKER = ".praxisforge-skill.json"
_MARKER_SCHEMA = "library-publication-v1"
_LEGACY_SCHEMA = "skill-publication-v1"
_SUFIXO = ".md"
_IGNORAR = shutil.ignore_patterns("__pycache__", SKILL_MARKER)


def _motivo(error: OSError) -> str:
    return error.strerror or type(error).__name__


def _apagar(caminho: Path) -> None:
    if caminho.is_symlink() or caminho.is_file():
        caminho.unlink()
    elif caminho.exists():
        shutil.rmtree(caminho)


def _gravar_atomico(destino: Path, conteudo: str) -> None:
    descritor, nome = tempfile.mkstemp(
        prefix=f".{destino.name}.", suffix=".tmp", dir=destino.parent
    )
    temporario = Path(nome)
    try:
        with os.fdopen(descritor, "w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(conteudo)
        os.replace(temporario, destino)
    except OSError:
        temporario.unlink(missing_ok=True)
        raise


class FilesystemItemPublisher(ItemPublisher):
    """
    Publica itens de `<library_dir>/<tipo>s/` em `<projeto>/.claude/<tipo>s/`.

    :param library_dir: pasta `library/` do repositório (absoluta — alvo dos symlinks).
    :type library_dir: Path
    :param validator: valida os marcadores (`library-publication-v1` e o legado da 008).
    :type validator: ContractValidator
    """

    def __init__(self, library_dir: Path, validator: ContractValidator) -> None:
        self._library_dir = library_dir.absolute()
        self._legacy_skills_dir = self._library_dir.parent / "skills"
        self._validator = validator

    # --- caminhos ------------------------------------------------------------------------------

    def _origem(self, kind: ItemKind, name: str) -> Path:
        base = self._library_dir / kind.directory
        return base / name if kind.is_folder else base / f"{name}{_SUFIXO}"

    @staticmethod
    def _pasta(project: Path, kind: ItemKind) -> Path:
        return project / ".claude" / kind.directory

    def _destino(self, project: Path, kind: ItemKind, name: str) -> Path:
        pasta = self._pasta(project, kind)
        return pasta / name if kind.is_folder else pasta / f"{name}{_SUFIXO}"

    def _marcador(self, project: Path, kind: ItemKind, name: str) -> Path:
        if kind.is_folder:
            return self._destino(project, kind, name) / SKILL_MARKER
        return self._pasta(project, kind) / f".{name}{_SUFIXO}.praxisforge.json"

    # --- leitura -------------------------------------------------------------------------------

    def _alvo_do_link(self, link: Path) -> Path:
        alvo = Path(os.readlink(link))
        if not alvo.is_absolute():
            alvo = link.parent / alvo
        return Path(os.path.normpath(alvo))

    def _ler_marcador(self, project: Path, kind: ItemKind, name: str) -> PublishedState | None:
        try:
            marcador = json.loads(self._marcador(project, kind, name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(marcador, dict) or marcador.get("name") != name:
            return None
        if marcador.get("kind") == kind.value and self._valido(marcador, _MARKER_SCHEMA):
            return PublishedState("copy", str(marcador["version"]), str(marcador["content_sha256"]))
        if (
            kind is ItemKind.SKILL
            and "kind" not in marcador
            and self._valido(marcador, _LEGACY_SCHEMA)
        ):
            return PublishedState(
                "copy",
                str(marcador["version"]),
                str(marcador["content_sha256"]),
                legacy_marker=True,
            )
        return None

    def _valido(self, marcador: dict[str, object], schema: str) -> bool:
        try:
            self._validator.validate(marcador, schema_name=schema)
        except PraxisForgeError:
            return False
        return True

    def inspect(self, project: Path, kind: ItemKind, name: str) -> PublishedState:
        """Ver ItemPublisher.inspect."""
        destino = self._destino(project, kind, name)
        if destino.is_symlink():
            alvo = self._alvo_do_link(destino)
            if alvo == self._origem(kind, name):
                return PublishedState("symlink")
            if kind is ItemKind.SKILL and alvo == self._legacy_skills_dir / name:
                return PublishedState("symlink" if alvo.exists() else "broken_symlink")
            return PublishedState("foreign")
        if not destino.exists():
            return PublishedState("absent")
        if kind.is_folder != destino.is_dir():
            return PublishedState("foreign")
        estado = self._ler_marcador(project, kind, name)
        return estado if estado is not None else PublishedState("foreign")

    # --- escrita -------------------------------------------------------------------------------

    def _trocar(self, novo: Path, destino: Path) -> None:
        """Coloca `novo` em `destino`; o antigo (nosso) sai só depois da troca bem-sucedida."""
        if not (destino.exists() or destino.is_symlink()):
            os.replace(novo, destino)
            return
        antigo = destino.parent / f".{destino.name}.old-{uuid.uuid4().hex[:8]}"
        os.replace(destino, antigo)
        try:
            os.replace(novo, destino)
        except OSError:
            os.replace(antigo, destino)
            raise
        _apagar(antigo)

    def _conteudo_marcador(
        self, kind: ItemKind, name: str, version: str, content_sha256: str
    ) -> str:
        marcador = {
            "schema_version": "1",
            "kind": kind.value,
            "name": name,
            "version": version,
            "content_sha256": content_sha256,
            "source": f"library/{kind.directory}/{name}",
        }
        return json.dumps(marcador, ensure_ascii=False, indent=2) + "\n"

    def publish_copy(
        self,
        project: Path,
        kind: ItemKind,
        name: str,
        version: str,
        content_sha256: str,
        references: list[Path],
    ) -> None:
        """Ver ItemPublisher.publish_copy."""
        pasta = self._pasta(project, kind)
        temporario: Path | None = None
        marcador = self._conteudo_marcador(kind, name, version, content_sha256)
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            if kind.is_folder:
                temporario = Path(tempfile.mkdtemp(prefix=f".{name}.tmp-", dir=pasta))
                shutil.copytree(
                    self._origem(kind, name), temporario, ignore=_IGNORAR, dirs_exist_ok=True
                )
                if references:
                    (temporario / "references").mkdir(exist_ok=True)
                    for referencia in references:
                        shutil.copy2(referencia, temporario / "references" / referencia.name)
                (temporario / SKILL_MARKER).write_text(marcador, encoding="utf-8")
                self._trocar(temporario, self._destino(project, kind, name))
                temporario = None
                return
            descritor, nome = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=pasta)
            os.close(descritor)
            temporario = Path(nome)
            shutil.copy2(self._origem(kind, name), temporario)
            self._trocar(temporario, self._destino(project, kind, name))
            temporario = None
            _gravar_atomico(self._marcador(project, kind, name), marcador)
        except OSError as error:
            raise SkillPublicationError(f"{kind.value}/{name}", _motivo(error)) from error
        finally:
            if temporario is not None:
                _apagar(temporario)

    def publish_symlink(self, project: Path, kind: ItemKind, name: str) -> None:
        """Ver ItemPublisher.publish_symlink."""
        pasta = self._pasta(project, kind)
        link = pasta / f".{name}.lnk-{uuid.uuid4().hex[:8]}"
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            os.symlink(self._origem(kind, name), link, target_is_directory=kind.is_folder)
            self._trocar(link, self._destino(project, kind, name))
            if not kind.is_folder:
                self._marcador(project, kind, name).unlink(missing_ok=True)
        except OSError as error:
            if link.is_symlink():
                link.unlink()
            raise SkillPublicationError(f"{kind.value}/{name}", _motivo(error)) from error

    def rewrite_marker(
        self, project: Path, kind: ItemKind, name: str, version: str, content_sha256: str
    ) -> None:
        """Ver ItemPublisher.rewrite_marker."""
        try:
            _gravar_atomico(
                self._marcador(project, kind, name),
                self._conteudo_marcador(kind, name, version, content_sha256),
            )
        except OSError as error:
            raise SkillPublicationError(f"{kind.value}/{name}", _motivo(error)) from error

    def remove(self, project: Path, kind: ItemKind, name: str) -> None:
        """Ver ItemPublisher.remove."""
        destino = self._destino(project, kind, name)
        if self.inspect(project, kind, name).kind not in ("copy", "symlink", "broken_symlink"):
            raise ForeignSkillDestinationError(name, str(destino))
        try:
            _apagar(destino)
            if not kind.is_folder:
                self._marcador(project, kind, name).unlink(missing_ok=True)
        except OSError as error:
            raise SkillPublicationError(f"{kind.value}/{name}", _motivo(error)) from error

    def list_published(self, project: Path, kind: ItemKind) -> list[str]:
        """Ver ItemPublisher.list_published."""
        pasta = self._pasta(project, kind)
        if not pasta.is_dir():
            return []
        nomes = []
        for item in pasta.iterdir():
            if item.name.startswith("."):
                continue
            if not kind.is_folder:
                if item.suffix != _SUFIXO:
                    continue
                nome = item.stem
            else:
                nome = item.name
            if self.inspect(project, kind, nome).kind in ("copy", "symlink", "broken_symlink"):
                nomes.append(nome)
        return sorted(nomes)
