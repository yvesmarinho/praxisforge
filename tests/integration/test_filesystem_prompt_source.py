# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_prompt_source.py
TITULO: Testes de falha — leitura dos prompts versionados em prompts/curation/ (feature 011)
DATA: 28/09/2026 15:52
MODIFICADO: 28/09/2026 15:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_prompt_source
HISTÓRICO:
    - 28/09/2026 15:52: criação (T010, feature 011)
STATUS: DEV
"""

import shutil
from pathlib import Path

import pytest

from praxisforge.domain.errors import PromptSetError
from praxisforge.infrastructure.filesystem_prompt_source import FilesystemPromptSource

ROOT = Path(__file__).parents[2]


def test_carrega_os_prompts_do_repositorio() -> None:
    prompts = FilesystemPromptSource(ROOT / "prompts" / "curation").load()
    assert "ARTEFATO_NAO_CONFIAVEL" in prompts.triage
    assert "out_of_scope" in prompts.criteria
    assert len(prompts.fingerprint) == 64


@pytest.mark.parametrize("faltando", ["triage.md", "draft.md", "judge.md", "criteria.md"])
def test_arquivo_ausente(tmp_path: Path, faltando: str) -> None:
    destino = tmp_path / "curation"
    shutil.copytree(ROOT / "prompts" / "curation", destino)
    (destino / faltando).unlink()
    with pytest.raises(PromptSetError, match=faltando) as erro:
        FilesystemPromptSource(destino).load()
    assert str(tmp_path) not in str(erro.value)


def test_arquivo_vazio(tmp_path: Path) -> None:
    destino = tmp_path / "curation"
    shutil.copytree(ROOT / "prompts" / "curation", destino)
    (destino / "judge.md").write_text("\n", encoding="utf-8")
    with pytest.raises(PromptSetError, match="judge.md"):
        FilesystemPromptSource(destino).load()


def test_mudanca_muda_impressao_digital(tmp_path: Path) -> None:
    destino = tmp_path / "curation"
    shutil.copytree(ROOT / "prompts" / "curation", destino)
    antes = FilesystemPromptSource(destino).load().fingerprint
    with (destino / "criteria.md").open("a", encoding="utf-8") as saida:
        saida.write("\nmais um critério\n")
    assert FilesystemPromptSource(destino).load().fingerprint != antes
