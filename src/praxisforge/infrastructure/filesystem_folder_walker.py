# -*- coding: utf-8 -*-
"""
NOME: filesystem_folder_walker.py
TITULO: Adapter FolderWalker — varredura somente leitura com exclusões e SHA-256
DATA: 25/09/2026 15:12
MODIFICADO: 25/09/2026 14:55
VERSÃO: 0.1.0
DEPEND: pathspec, praxisforge.application.ports
HISTÓRICO:
    - 25/09/2026 15:12: criação (T017, feature 010) — faz test_filesystem_folder_walker.py passar
STATUS: DEV
"""

import hashlib
import logging
import os
from pathlib import Path

import pathspec

from praxisforge.application.ports import FolderWalk, FolderWalker, WalkedFile
from praxisforge.domain.curation_artifact import ExcludedEntry, ExclusionReason
from praxisforge.domain.errors import FolderPathInvalidError, FolderPathUnreadableError

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 262_144
"""Maior arquivo aceito (256 KiB); acima disso, exclusão `too_large` (FR-006)."""

FIXED_DIRS = frozenset(
    {".git", "node_modules", ".venv", "__pycache__", "dist", "build", "graphify-out"}
)
_BINARY_PROBE = 8192

_Specs = list[tuple[str, pathspec.GitIgnoreSpec]]


def _join(rel: str, name: str) -> str:
    return f"{rel}/{name}" if rel else name


class FilesystemFolderWalker(FolderWalker):
    """
    Percorre a pasta sem seguir links de diretório (sem ciclos) e sem escrever nela.

    Ordem das exclusões: lista fixa de diretórios → `.gitignore` (pai antes do filho, negação
    respeitada) → links → tamanho → ilegível → binário (byte NUL nos primeiros 8 KiB).
    """

    def walk(self, root: Path) -> FolderWalk:
        """Ver FolderWalker.walk."""
        if not root.is_dir():
            raise FolderPathInvalidError(root.name, "não existe ou não é diretório")
        real_root = root.resolve()
        files: list[WalkedFile] = []
        excluded: list[ExcludedEntry] = []
        try:
            entradas = sorted(os.scandir(real_root), key=lambda e: e.name)
        except PermissionError as error:
            raise FolderPathUnreadableError(root.name) from error
        self._visitar(real_root, real_root, "", entradas, [], files, excluded)
        return FolderWalk(
            files=tuple(sorted(files, key=lambda f: f.path)),
            excluded=tuple(sorted(excluded, key=lambda e: e.path)),
        )

    def _visitar(
        self,
        real_root: Path,
        diretorio: Path,
        rel: str,
        entradas: list[os.DirEntry[str]],
        specs: _Specs,
        files: list[WalkedFile],
        excluded: list[ExcludedEntry],
    ) -> None:
        specs = specs + self._gitignore(diretorio, rel)
        for entrada in entradas:
            filho = _join(rel, entrada.name)
            if entrada.is_symlink():
                self._link(real_root, Path(entrada.path), filho, specs, files, excluded)
            elif entrada.is_dir(follow_symlinks=False):
                self._diretorio(real_root, Path(entrada.path), filho, specs, files, excluded)
            elif _ignorado(specs, filho, is_dir=False):
                excluded.append(ExcludedEntry(filho, ExclusionReason.GITIGNORE, False))
            elif entrada.is_file(follow_symlinks=False):
                self._arquivo(Path(entrada.path), filho, files, excluded)
            else:  # fifo, socket, dispositivo
                excluded.append(ExcludedEntry(filho, ExclusionReason.UNREADABLE, False))

    def _diretorio(
        self,
        real_root: Path,
        caminho: Path,
        rel: str,
        specs: _Specs,
        files: list[WalkedFile],
        excluded: list[ExcludedEntry],
    ) -> None:
        if caminho.name in FIXED_DIRS:
            excluded.append(ExcludedEntry(rel, ExclusionReason.FIXED_DIR, True))
            return
        if _ignorado(specs, rel, is_dir=True):
            excluded.append(ExcludedEntry(rel, ExclusionReason.GITIGNORE, True))
            return
        try:
            entradas = sorted(os.scandir(caminho), key=lambda e: e.name)
        except OSError:
            logger.warning("diretório ilegível no inventário: %s", rel)
            excluded.append(ExcludedEntry(rel, ExclusionReason.UNREADABLE, True))
            return
        self._visitar(real_root, caminho, rel, entradas, specs, files, excluded)

    def _link(
        self,
        real_root: Path,
        caminho: Path,
        rel: str,
        specs: _Specs,
        files: list[WalkedFile],
        excluded: list[ExcludedEntry],
    ) -> None:
        if _ignorado(specs, rel, is_dir=caminho.is_dir()):
            excluded.append(ExcludedEntry(rel, ExclusionReason.GITIGNORE, caminho.is_dir()))
        elif caminho.is_dir():
            excluded.append(ExcludedEntry(rel, ExclusionReason.SYMLINK_DIR, True))
        elif not caminho.exists():
            excluded.append(ExcludedEntry(rel, ExclusionReason.UNREADABLE, False))
        elif not caminho.resolve().is_relative_to(real_root):
            excluded.append(ExcludedEntry(rel, ExclusionReason.SYMLINK_OUTSIDE, False))
        else:
            self._arquivo(caminho.resolve(), rel, files, excluded)

    def _arquivo(
        self, caminho: Path, rel: str, files: list[WalkedFile], excluded: list[ExcludedEntry]
    ) -> None:
        try:
            tamanho = caminho.stat().st_size
            if tamanho > MAX_FILE_SIZE:
                excluded.append(ExcludedEntry(rel, ExclusionReason.TOO_LARGE, False))
                return
            conteudo = caminho.read_bytes()
        except OSError:
            logger.warning("arquivo ilegível no inventário: %s", rel)
            excluded.append(ExcludedEntry(rel, ExclusionReason.UNREADABLE, False))
            return
        if b"\0" in conteudo[:_BINARY_PROBE]:
            excluded.append(ExcludedEntry(rel, ExclusionReason.BINARY, False))
            return
        files.append(WalkedFile(rel, len(conteudo), hashlib.sha256(conteudo).hexdigest()))

    @staticmethod
    def _gitignore(diretorio: Path, rel: str) -> _Specs:
        arquivo = diretorio / ".gitignore"
        if not arquivo.is_file() or arquivo.is_symlink():
            return []
        try:
            linhas = arquivo.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            logger.warning("gitignore ilegível no inventário: %s", _join(rel, ".gitignore"))
            return []
        return [(rel, pathspec.GitIgnoreSpec.from_lines(linhas))]


def _ignorado(specs: _Specs, rel: str, *, is_dir: bool) -> bool:
    """Última decisão definitiva vence (filho sobrepõe pai), como no git."""
    decisao = False
    for base, spec in specs:
        relativo = rel[len(base) + 1 :] if base else rel
        resultado = spec.check_file(f"{relativo}/" if is_dir else relativo)
        if resultado.include is not None:
            decisao = resultado.include
    return decisao
