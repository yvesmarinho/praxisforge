# -*- coding: utf-8 -*-
"""
NOME: test_skill_template.py
TITULO: Testes de contrato — skills/_template/SKILL.md (feature 008)
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema, pyyaml
HISTÓRICO:
    - 24/09/2026 16:54: criação (T015, feature 008)
STATUS: DEV
"""

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from praxisforge.infrastructure.filesystem_skill_repository import FilesystemSkillRepository

ROOT = Path(__file__).parents[2]
TEMPLATE = ROOT / "skills" / "_template" / "SKILL.md"


def _partes() -> tuple[dict[str, object], str]:
    _, bloco, corpo = TEMPLATE.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(bloco), corpo


def test_template_existe_com_frontmatter_valido() -> None:
    """O template tem frontmatter válido no skill-frontmatter-v1."""
    frontmatter, _ = _partes()
    schema = json.loads(
        (ROOT / "schemas" / "skill-frontmatter-v1.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(frontmatter)) == []


def test_template_tem_instrucoes_de_preenchimento() -> None:
    """O corpo explica versão, fontes/autoral e arquivos de apoio."""
    _, corpo = _partes()
    for termo in ("metadata.version", "sources", "authored", "link relativo"):
        assert termo in corpo


def test_template_nao_e_listado_como_skill() -> None:
    """A pasta _template não aparece na lista de skills."""
    assert "_template" not in FilesystemSkillRepository(ROOT / "skills").list_names()


def test_skill_copiada_do_template_valida(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Copiar o template, renomear e marcar como autoral basta para validar (bug T042)."""
    from praxisforge.presentation.cli import main
    from tests.skills_helpers import criar_projeto

    root = criar_projeto(tmp_path / "projeto")
    texto = TEMPLATE.read_text(encoding="utf-8")
    texto = texto.replace("name: nome-da-skill", "name: copia").replace(
        "authored: false", "authored: true"
    )
    (root / "skills" / "copia").mkdir()
    (root / "skills" / "copia" / "SKILL.md").write_text(
        texto.replace("  sources: [slug-da-fonte]\n", ""), encoding="utf-8"
    )
    monkeypatch.chdir(root)
    assert main(["skills", "validate", "copia"]) == 0, capsys.readouterr().out
