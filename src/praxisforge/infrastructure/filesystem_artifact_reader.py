# -*- coding: utf-8 -*-
"""
NOME: filesystem_artifact_reader.py
TITULO: Adapter ArtifactReader — conteúdo de um artefato da pasta curada (só leitura, 011)
DATA: 28/09/2026 16:01
MODIFICADO: 28/09/2026 16:01
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports
HISTÓRICO:
    - 28/09/2026 16:01: criação (T028, feature 011) — faz test_filesystem_artifact_reader.py passar
STATUS: DEV
"""

from pathlib import Path

from praxisforge.application.ports import ArtifactReader
from praxisforge.domain.errors import ArtifactTooLargeError, FolderPathInvalidError

ARTIFACT_LIMIT = 256 * 1024
_PRINCIPAIS = ("SKILL.md", "HOOK.md", "README.md")


class FilesystemArtifactReader(ArtifactReader):
    """
    Lê o artefato sem escrever nada: arquivo único, ou diretório com o arquivo principal primeiro
    e os arquivos de apoio de texto em ordem de caminho. Links simbólicos e binários ficam de fora;
    acima de 256 KiB, falha sem truncar (FR-011b).
    """

    def read(self, folder: Path, artifact_path: str) -> str:
        """Ver ArtifactReader.read."""
        raiz = folder.resolve()
        alvo = folder / artifact_path
        if Path(artifact_path).is_absolute() or alvo.is_symlink() or not alvo.exists():
            raise FolderPathInvalidError(artifact_path, reason="artefato inacessível")
        if not alvo.resolve().is_relative_to(raiz):
            raise FolderPathInvalidError(artifact_path, reason="artefato fora da pasta")
        if alvo.is_file():
            return self._limitar(artifact_path, self._texto(alvo) or "")
        partes: list[str] = []
        for arquivo in self._arquivos(alvo):
            texto = self._texto(arquivo)
            if texto is not None:
                partes.append(f"=== {arquivo.relative_to(alvo).as_posix()} ===\n{texto}")
        return self._limitar(artifact_path, "\n\n".join(partes))

    @staticmethod
    def _arquivos(diretorio: Path) -> list[Path]:
        todos = sorted(p for p in diretorio.rglob("*") if p.is_file() and not p.is_symlink())
        principais = [p for p in todos if p.parent == diretorio and p.name in _PRINCIPAIS]
        principal = principais[:1]
        return principal + [p for p in todos if p not in principal]

    @staticmethod
    def _texto(arquivo: Path) -> str | None:
        try:
            dados = arquivo.read_bytes()
        except OSError:
            return None
        if b"\0" in dados:
            return None
        return dados.decode("utf-8", errors="replace")

    @staticmethod
    def _limitar(artifact_path: str, texto: str) -> str:
        tamanho = len(texto.encode("utf-8"))
        if tamanho > ARTIFACT_LIMIT:
            raise ArtifactTooLargeError(artifact_path, tamanho, ARTIFACT_LIMIT)
        return texto
