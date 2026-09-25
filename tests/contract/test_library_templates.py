# -*- coding: utf-8 -*-
"""
NOME: test_library_templates.py
TITULO: Testes de contrato — templates do acervo (library/_templates/)
DATA: 25/09/2026 13:12
MODIFICADO: 25/09/2026 13:12
VERSÃO: 0.1.0
DEPEND: pytest, pyyaml, jsonschema, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 13:12: criação (T021, feature 009) — sucede test_skill_template.py
STATUS: DEV
"""

import json
import os
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from praxisforge.presentation.cli import main
from tests.library_helpers import criar_projeto

ROOT = Path(__file__).parents[2]
TEMPLATES = ROOT / "library" / "_templates"
# tipo → (template, destino relativo a library/, nome no frontmatter?)
CASOS = {
    "skill": ("skill", "skills/copia", "nome-da-skill"),
    "command": ("command.md", "commands/copia.md", None),
    "agent": ("agent.md", "agents/copia.md", "nome-do-agente"),
    "hook": ("hook", "hooks/copia", "nome-do-hook"),
    "rule": ("rule.md", "rules/copia.md", None),
    "reference": ("reference.md", "references/copia.md", "nome-da-reference"),
}


def _principal(tipo: str) -> Path:
    origem = TEMPLATES / CASOS[tipo][0]
    if origem.is_dir():
        return origem / ("SKILL.md" if tipo == "skill" else "HOOK.md")
    return origem


def _partes(tipo: str) -> tuple[dict[str, object], str]:
    _, bloco, corpo = _principal(tipo).read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(bloco), corpo


@pytest.mark.parametrize("tipo", list(CASOS))
def test_template_tem_frontmatter_valido_no_schema(tipo: str) -> None:
    """Cada template passa no <tipo>-frontmatter-v1."""
    frontmatter, _ = _partes(tipo)
    schema = json.loads((ROOT / "schemas" / f"{tipo}-frontmatter-v1.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(frontmatter)) == []


@pytest.mark.parametrize("tipo", list(CASOS))
def test_template_tem_instrucoes(tipo: str) -> None:
    """O corpo explica versão, fontes (só ideias) e autoria."""
    _, corpo = _partes(tipo)
    for termo in ("metadata.version", "sources", "authored", "ideias"):
        assert termo in corpo, termo


def test_script_do_hook_executavel() -> None:
    """O run.sh do template de hook é executável (I4)."""
    assert os.access(TEMPLATES / "hook" / "run.sh", os.X_OK)


@pytest.mark.parametrize("tipo", list(CASOS))
def test_copia_do_template_valida(
    tipo: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Uma cópia preenchida só nos campos marcados passa em library validate (SC-001)."""
    origem_rel, destino_rel, nome_template = CASOS[tipo]
    root = criar_projeto(tmp_path / "projeto")
    destino = root / "library" / destino_rel
    origem = TEMPLATES / origem_rel
    if origem.is_dir():
        shutil.copytree(origem, destino)
        principal = destino / ("SKILL.md" if tipo == "skill" else "HOOK.md")
    else:
        shutil.copy2(origem, destino)
        principal = destino
    texto = principal.read_text(encoding="utf-8")
    if nome_template:
        texto = texto.replace(f"name: {nome_template}", "name: copia")
    texto = texto.replace("authored: false", "authored: true")
    principal.write_text(texto.replace("  sources: [slug-da-fonte]\n", ""), encoding="utf-8")
    monkeypatch.chdir(root)
    assert main(["library", "validate", "--type", tipo, "copia"]) == 0, capsys.readouterr().out
