# -*- coding: utf-8 -*-
"""
NOME: filesystem_skill_publisher.py
TITULO: Adapter de SkillPublisher — cópia atômica com marcador, symlink e remoção segura
DATA: 24/09/2026 16:50
MODIFICADO: 24/09/2026 16:50
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.errors, praxisforge.application.ports
HISTÓRICO:
    - 24/09/2026 16:50: criação (T034, feature 008)
STATUS: DEV
"""

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from praxisforge.application.ports import ContractValidator, PublishedState, SkillPublisher
from praxisforge.domain.errors import (
    ForeignSkillDestinationError,
    PraxisForgeError,
    SkillPublicationError,
)

MARKER_FILE = ".praxisforge-skill.json"
_MARKER_SCHEMA = "skill-publication-v1"
_IGNORAR = shutil.ignore_patterns("__pycache__", MARKER_FILE)


def _motivo(error: OSError) -> str:
    return error.strerror or type(error).__name__


def _apagar(caminho: Path) -> None:
    if caminho.is_symlink() or caminho.is_file():
        caminho.unlink()
    elif caminho.exists():
        shutil.rmtree(caminho)


class FilesystemSkillPublisher(SkillPublisher):
    """
    Publica skills de `<skills_dir>/<nome>` em uma pasta `.claude/skills`.

    :param skills_dir: pasta `skills/` do repositório (absoluta — alvo dos symlinks).
    :type skills_dir: Path
    :param validator: valida o marcador contra `skill-publication-v1`.
    :type validator: ContractValidator
    """

    def __init__(self, skills_dir: Path, validator: ContractValidator) -> None:
        self._skills_dir = skills_dir.absolute()
        self._validator = validator

    def _origem(self, name: str) -> Path:
        return self._skills_dir / name

    def _link_nosso(self, destino: Path, name: str) -> bool:
        alvo = Path(os.readlink(destino))
        if not alvo.is_absolute():
            alvo = destino.parent / alvo
        return Path(os.path.normpath(alvo)) == self._origem(name)

    def _ler_marcador(self, destino: Path, name: str) -> dict[str, object] | None:
        try:
            marcador = json.loads((destino / MARKER_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(marcador, dict) or marcador.get("name") != name:
            return None
        try:
            self._validator.validate(marcador, schema_name=_MARKER_SCHEMA)
        except PraxisForgeError:
            return None
        return marcador

    def inspect(self, dest_root: Path, name: str) -> PublishedState:
        """Ver SkillPublisher.inspect."""
        destino = dest_root / name
        if destino.is_symlink():
            return PublishedState("symlink" if self._link_nosso(destino, name) else "foreign")
        if not destino.exists():
            return PublishedState("absent")
        if not destino.is_dir():
            return PublishedState("foreign")
        marcador = self._ler_marcador(destino, name)
        if marcador is None:
            return PublishedState("foreign")
        return PublishedState("copy", str(marcador["version"]), str(marcador["content_sha256"]))

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

    def publish_copy(self, dest_root: Path, name: str, version: str, content_sha256: str) -> None:
        """Ver SkillPublisher.publish_copy."""
        temporario: Path | None = None
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
            temporario = Path(tempfile.mkdtemp(prefix=f".{name}.tmp-", dir=dest_root))
            shutil.copytree(self._origem(name), temporario, ignore=_IGNORAR, dirs_exist_ok=True)
            marcador = {
                "schema_version": "1",
                "name": name,
                "version": version,
                "content_sha256": content_sha256,
                "source": f"skills/{name}",
            }
            (temporario / MARKER_FILE).write_text(
                json.dumps(marcador, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            self._trocar(temporario, dest_root / name)
            temporario = None
        except OSError as error:
            raise SkillPublicationError(name, _motivo(error)) from error
        finally:
            if temporario is not None:
                shutil.rmtree(temporario, ignore_errors=True)

    def publish_symlink(self, dest_root: Path, name: str) -> None:
        """Ver SkillPublisher.publish_symlink."""
        link = dest_root / f".{name}.lnk-{uuid.uuid4().hex[:8]}"
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
            os.symlink(self._origem(name), link, target_is_directory=True)
            self._trocar(link, dest_root / name)
        except OSError as error:
            if link.is_symlink():
                link.unlink()
            raise SkillPublicationError(name, _motivo(error)) from error

    def remove(self, dest_root: Path, name: str) -> None:
        """Ver SkillPublisher.remove."""
        destino = dest_root / name
        if self.inspect(dest_root, name).kind not in ("copy", "symlink"):
            raise ForeignSkillDestinationError(name, str(destino))
        try:
            _apagar(destino)
        except OSError as error:
            raise SkillPublicationError(name, _motivo(error)) from error

    def list_published(self, dest_root: Path) -> list[str]:
        """Ver SkillPublisher.list_published."""
        if not dest_root.is_dir():
            return []
        return sorted(
            item.name
            for item in dest_root.iterdir()
            if not item.name.startswith(".")
            and self.inspect(dest_root, item.name).kind in ("copy", "symlink")
        )
