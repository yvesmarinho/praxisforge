# -*- coding: utf-8 -*-
"""
NOME: test_library_migration.py
TITULO: Testes de integração — acervo migrado de skills/ para library/ (repositório real)
DATA: 25/09/2026 13:12
MODIFICADO: 25/09/2026 13:12
VERSÃO: 0.1.0
DEPEND: pytest, pyyaml, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 13:12: criação (T022, feature 009)
STATUS: DEV
"""

from pathlib import Path

import pytest
import yaml

from praxisforge.presentation.cli import main

ROOT = Path(__file__).parents[2]
SKILLS = ROOT / "library" / "skills"


def _metadata(nome: str) -> dict[str, object]:
    _, bloco, _ = (SKILLS / nome / "SKILL.md").read_text(encoding="utf-8").split("---\n", 2)
    meta = yaml.safe_load(bloco)["metadata"]
    assert isinstance(meta, dict)
    return meta


def test_diretorio_antigo_nao_existe() -> None:
    """skills/ saiu do repositório (FR-015, FR-016)."""
    assert not (ROOT / "skills").exists()


def test_skills_migradas() -> None:
    """As 2 skills da 008 estão em library/skills/ (SC-002)."""
    nomes = sorted(p.name for p in SKILLS.iterdir() if p.is_dir())
    assert {"diretrizes-codificacao", "guarda-barra-qualidade"} <= set(nomes)


def test_diretrizes_inalterada() -> None:
    """diretrizes-codificacao segue na versão 1.0.0, sem reescrita pendente."""
    meta = _metadata("diretrizes-codificacao")
    assert meta["version"] == "1.0.0"
    assert "rewrite_pending" not in meta


def test_guarda_barra_marcada_para_reescrita() -> None:
    """guarda-barra-qualidade: rewrite_pending e versão 1.0.1 (FR-025)."""
    meta = _metadata("guarda-barra-qualidade")
    assert (meta["version"], meta["rewrite_pending"]) == ("1.0.1", True)
    assert (SKILLS / "guarda-barra-qualidade" / "LICENSE.agent-skills").is_file()


def test_acervo_real_valida(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """O acervo real passa em library validate."""
    monkeypatch.chdir(ROOT)
    codigo = main(["library", "validate"])
    saida = capsys.readouterr().out
    assert codigo == 0, saida
    assert "skill/guarda-barra-qualidade: reescrita pendente" in saida
