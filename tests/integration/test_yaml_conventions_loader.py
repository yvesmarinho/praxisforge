# -*- coding: utf-8 -*-
"""
NOME: test_yaml_conventions_loader.py
TITULO: Testes de falha — leitura das convenções de curadoria junto do registro (feature 010)
DATA: 25/09/2026 15:02
MODIFICADO: 28/09/2026 15:12
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.yaml_conventions_loader
HISTÓRICO:
    - 25/09/2026 15:02: criação (T011, feature 010)
    - 28/09/2026 15:12: layouts reais das pastas (skills aninhadas/na raiz, agents por
      categoria, Copilot)
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


@pytest.mark.parametrize(
    ("caminho", "esperado"),
    [
        ("cli-tool/components/agents/data-ai/a.md", ArtifactKind.AGENT),
        ("instructions/python.instructions.md", ArtifactKind.RULE),
        (".github/prompts/p.prompt.md", ArtifactKind.COMMAND),
        ("agents/sub/x.agent.md", ArtifactKind.AGENT),
        ("chatmodes/m.chatmode.md", ArtifactKind.AGENT),
        ("rules/python/estilo.md", ArtifactKind.RULE),
        ("docs/guia.md", None),
    ],
)
def test_exemplo_cobre_layouts_reais_de_arquivo(
    tmp_path: Path, caminho: str, esperado: ArtifactKind | None
) -> None:
    destino = tmp_path / "curation-conventions.yaml"
    shutil.copy(EXEMPLO, destino)
    assert _fonte(destino).load().classify_file(caminho) is esperado


@pytest.mark.parametrize("diretorio", ["cli-tool/components/skills/development/x", "canvas-design"])
def test_exemplo_cobre_skills_aninhadas_e_na_raiz(tmp_path: Path, diretorio: str) -> None:
    destino = tmp_path / "curation-conventions.yaml"
    shutil.copy(EXEMPLO, destino)
    conv = _fonte(destino).load()
    assert conv.classify_directory(diretorio, frozenset({"SKILL.md"})) is ArtifactKind.SKILL
    assert conv.classify_directory(diretorio, frozenset({"README.md"})) is None


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
