# -*- coding: utf-8 -*-
"""
NOME: test_yaml_conventions_loader.py
TITULO: Testes de falha — leitura das convenções de curadoria junto do registro (feature 010)
DATA: 25/09/2026 15:02
MODIFICADO: 25/09/2026 14:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.yaml_conventions_loader
HISTÓRICO:
    - 25/09/2026 15:02: criação (T011, feature 010)
STATUS: DEV
"""

import os
import shutil
from pathlib import Path

import pytest

from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.errors import ConventionsError, ConventionsMissingError
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.yaml_conventions_loader import YamlConventionsSource

ROOT = Path(__file__).parents[2]
EXEMPLO = ROOT / "src" / "data" / "curation-conventions.example.yaml"


def _fonte(path: Path) -> YamlConventionsSource:
    return YamlConventionsSource(path, JsonSchemaContractValidator(schemas_dir=ROOT / "schemas"))


def test_carrega_o_exemplo(tmp_path: Path) -> None:
    destino = tmp_path / "curation-conventions.yaml"
    shutil.copy(EXEMPLO, destino)
    conv = _fonte(destino).load()
    assert conv.classify_directory("skills/x", frozenset({"SKILL.md"})) is ArtifactKind.SKILL
    assert conv.classify_file(".claude/commands/c.md") is ArtifactKind.COMMAND
    assert conv.classify_file("AGENTS.md") is ArtifactKind.PROJECT_INSTRUCTION


def test_ausente_explica_como_criar(tmp_path: Path) -> None:
    with pytest.raises(ConventionsMissingError, match="curation-conventions.example.yaml"):
        _fonte(tmp_path / "curation-conventions.yaml").load()


@pytest.mark.parametrize(
    "conteudo",
    [
        "rules: [\n",  # YAML inválido
        "- a\n- b\n",  # não é mapeamento
        'schema_version: "1"\nrules: []\n',  # schema
        'schema_version: "9"\nrules: [{kind: skill, pattern: x, unit: file}]\n',  # versão
        'schema_version: "1"\nrules: [{kind: unknown, pattern: x, unit: file}]\n',
    ],
)
def test_invalido(tmp_path: Path, conteudo: str) -> None:
    destino = tmp_path / "c.yaml"
    destino.write_text(conteudo, encoding="utf-8")
    with pytest.raises(ConventionsError):
        _fonte(destino).load()


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_ilegivel(tmp_path: Path) -> None:
    destino = tmp_path / "c.yaml"
    shutil.copy(EXEMPLO, destino)
    destino.chmod(0)
    try:
        with pytest.raises(ConventionsError):
            _fonte(destino).load()
    finally:
        destino.chmod(0o600)
