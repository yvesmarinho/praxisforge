# -*- coding: utf-8 -*-
"""
NOME: filesystem_library_repository.py
TITULO: Adapter de LibraryRepository sobre o filesystem (library/<tipo>s/...)
DATA: 25/09/2026 13:03
MODIFICADO: 25/09/2026 13:03
VERSÃO: 0.1.0
DEPEND: pyyaml, praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 25/09/2026 13:03: criação (T014, feature 009) — generaliza filesystem_skill_repository.py
STATUS: DEV
"""

import hashlib
from pathlib import Path

import yaml

from praxisforge.application.ports import ItemDocument, LibraryRepository
from praxisforge.domain.errors import (
    InvalidLibraryItemError,
    LibraryItemNotFoundError,
    LibraryNotFoundError,
    Violation,
)
from praxisforge.domain.library_item import ItemKind
from praxisforge.domain.skill import extract_references
from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader

_DELIMITER = "---"
_SUFFIX = ".md"
MARKER_FILE = ".praxisforge-skill.json"
_IGNORED_DIRS = ("__pycache__",)
_RESERVED = ("INDEX.md", "_templates")


def _ignorado(nome: str) -> bool:
    return nome.startswith(("_", "."))


def _invalido(kind: ItemKind, name: str, arquivo: str, reason: str) -> InvalidLibraryItemError:
    return InvalidLibraryItemError(kind.value, name, [Violation(arquivo, reason)])


def _split_frontmatter(
    kind: ItemKind, name: str, arquivo: str, conteudo: str
) -> tuple[dict[str, object], str]:
    linhas = conteudo.split("\n")
    if linhas[0].strip() != _DELIMITER:
        raise _invalido(kind, name, arquivo, "sem frontmatter")
    try:
        fim = linhas[1:].index(_DELIMITER) + 1
    except ValueError as error:
        raise _invalido(kind, name, arquivo, "frontmatter não fechado") from error
    try:
        # NoTimestampSafeLoader só remove o resolvedor de timestamp do SafeLoader
        documento = yaml.load("\n".join(linhas[1:fim]), Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
    except yaml.YAMLError as error:
        raise _invalido(kind, name, arquivo, f"frontmatter corrompido: {error}") from error
    if not isinstance(documento, dict):
        raise _invalido(kind, name, arquivo, "frontmatter não é um mapa")
    return documento, "\n".join(linhas[fim + 1 :])


def _dentro(pasta: Path, relativo: str) -> Path | None:
    """Caminho do alvo quando fica dentro da pasta; None quando sai dela (a entidade acusa)."""
    if relativo.startswith(("/", "\\")) or ":" in relativo:
        return None
    alvo = (pasta / relativo).resolve()
    return alvo if alvo.is_relative_to(pasta.resolve()) else None


def _ausentes(pasta: Path, relativos: list[str]) -> list[str]:
    ausentes = []
    for relativo in relativos:
        alvo = _dentro(pasta, relativo)
        if alvo is not None and not alvo.exists():
            ausentes.append(relativo)
    return ausentes


class FilesystemLibraryRepository(LibraryRepository):
    """
    Lê o acervo em `<library_dir>/<tipo>s/`.

    :param library_dir: pasta `library/` do repositório.
    :type library_dir: Path
    """

    def __init__(self, library_dir: Path) -> None:
        self._library_dir = library_dir

    def _exigir_acervo(self) -> None:
        if not self._library_dir.is_dir():
            raise LibraryNotFoundError()

    def list_entries(self, kind: ItemKind) -> list[str]:
        """Ver LibraryRepository.list_entries."""
        self._exigir_acervo()
        base = self._library_dir / kind.directory
        if not base.is_dir():
            return []
        if kind.is_folder:
            return sorted(p.name for p in base.iterdir() if p.is_dir() and not _ignorado(p.name))
        return sorted(
            p.stem
            for p in base.iterdir()
            if p.is_file() and p.suffix == _SUFFIX and not _ignorado(p.name)
        )

    def unknown_entries(self) -> list[str]:
        """Ver LibraryRepository.unknown_entries."""
        self._exigir_acervo()
        diretorios = {kind.directory: kind for kind in ItemKind}
        desconhecidos: list[str] = []
        for entrada in self._library_dir.iterdir():
            if entrada.name in _RESERVED or _ignorado(entrada.name):
                continue
            kind = diretorios.get(entrada.name) if entrada.is_dir() else None
            if kind is None:
                desconhecidos.append(entrada.name)
                continue
            for item in entrada.iterdir():
                if _ignorado(item.name):
                    continue
                valido = (
                    item.is_dir() if kind.is_folder else (item.is_file() and item.suffix == _SUFFIX)
                )
                if not valido:
                    desconhecidos.append(f"{entrada.name}/{item.name}")
        return sorted(desconhecidos)

    def item_path(self, kind: ItemKind, name: str) -> Path:
        """Ver LibraryRepository.item_path."""
        base = self._library_dir / kind.directory
        return base / name if kind.is_folder else base / f"{name}{_SUFFIX}"

    def load(self, kind: ItemKind, name: str) -> ItemDocument:
        """Ver LibraryRepository.load."""
        self._exigir_acervo()
        caminho = self.item_path(kind, name)
        if kind.is_folder:
            if not caminho.is_dir():
                raise LibraryItemNotFoundError(kind.value, name)
            nome_arquivo = str(kind.main_file)
            arquivo = caminho / nome_arquivo
            if not arquivo.is_file():
                raise _invalido(kind, name, nome_arquivo, "arquivo ausente")
            pasta = caminho
        else:
            if not caminho.is_file():
                raise LibraryItemNotFoundError(kind.value, name)
            nome_arquivo = caminho.name
            arquivo = caminho
            pasta = caminho.parent
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise _invalido(
                kind, name, nome_arquivo, f"ilegível ({type(error).__name__})"
            ) from error
        frontmatter, corpo = _split_frontmatter(kind, name, nome_arquivo, conteudo)
        referencias = extract_references(corpo)
        ausentes = _ausentes(pasta, referencias) if kind.is_folder else []
        if kind is ItemKind.HOOK:
            run = frontmatter.get("run")
            if isinstance(run, list):
                ausentes.extend(_ausentes(pasta, [r for r in run if isinstance(r, str) and r]))
        return ItemDocument(
            kind=kind,
            entry_name=name,
            frontmatter=frontmatter,
            support_files=referencias,
            missing_files=ausentes,
        )

    def content_hash(self, kind: ItemKind, name: str) -> str:
        """Ver LibraryRepository.content_hash (mesmo algoritmo da 008 para pastas)."""
        caminho = self.item_path(kind, name)
        digest = hashlib.sha256()
        if kind.is_folder:
            arquivos = sorted(
                item
                for item in caminho.rglob("*")
                if item.is_file()
                and item.name != MARKER_FILE
                and not any(parte in _IGNORED_DIRS for parte in item.relative_to(caminho).parts)
            )
            base = caminho
        else:
            arquivos = [caminho]
            base = caminho.parent
        for item in arquivos:
            digest.update(item.relative_to(base).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(item.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()
