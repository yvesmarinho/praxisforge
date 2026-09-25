# -*- coding: utf-8 -*-
"""
NOME: test_skill_schemas.py
TITULO: Testes de contrato — skill-frontmatter-v1 e skill-publication-v1 (feature 008)
DATA: 24/09/2026 16:40
MODIFICADO: 25/09/2026 12:59
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 24/09/2026 16:40: criação (T002, feature 008)
    - 25/09/2026 12:59: skill-frontmatter-v1 passa a ser comparado com o contrato da 009
STATUS: DEV
"""

import json
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[2]
CONTRATOS = ROOT / "specs" / "008-biblioteca-skills" / "contracts"
# skill-frontmatter-v1 evoluiu (aditivo) na 009 e é comparado com o contrato da 009
# em test_library_schemas.py
NOMES = ("skill-publication-v1.json",)


def _carregar(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _sem_meta(documento: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in documento.items() if key != "_meta"}


def _erros(nome: str, documento: dict[str, object]) -> list[str]:
    validator = Draft202012Validator(_carregar(ROOT / "schemas" / nome))
    return [error.message for error in validator.iter_errors(documento)]


@pytest.mark.parametrize("nome", NOMES)
def test_schema_valido_e_identico_ao_contrato(nome: str) -> None:
    """schemas/<nome> é Draft 2020-12 válido e idêntico (sem _meta) ao contrato da 008."""
    runtime = _carregar(ROOT / "schemas" / nome)
    Draft202012Validator.check_schema(runtime)
    assert _sem_meta(runtime) == _sem_meta(_carregar(CONTRATOS / nome))


def _skill(**campos: object) -> dict[str, object]:
    documento: dict[str, object] = {
        "name": "revisar-codigo",
        "description": "Revisa código Python",
        "metadata": {"version": "1.0.0", "sources": ["guia-a"], "authored": False},
    }
    documento.update(campos)
    return documento


def test_frontmatter_valido_com_campos_extras() -> None:
    """Aceita campos do formato do Claude na raiz (allowed-tools) e licença."""
    assert (
        _erros("skill-frontmatter-v1.json", _skill(**{"allowed-tools": "Read", "license": "MIT"}))
        == []
    )


@pytest.mark.parametrize("nome", ["Revisar", "revisar codigo", "a" * 65, "-x", "x-", ""])
def test_frontmatter_rejeita_nome_fora_do_formato(nome: str) -> None:
    """name com maiúsculas, espaço, >64, hífen nas pontas ou vazio é rejeitado."""
    assert _erros("skill-frontmatter-v1.json", _skill(name=nome))


@pytest.mark.parametrize("descricao", ["", "x" * 1025])
def test_frontmatter_rejeita_descricao_vazia_ou_longa(descricao: str) -> None:
    """description vazia ou com mais de 1024 caracteres é rejeitada."""
    assert _erros("skill-frontmatter-v1.json", _skill(description=descricao))


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"version": "1"},
        {"version": "1.0"},
        {"version": "v1.0.0"},
        {"version": "1.0.0", "sources": ["a", "a"]},
        {"version": "1.0.0", "authored": "sim"},
    ],
)
def test_frontmatter_rejeita_metadata_invalida(metadata: dict[str, object]) -> None:
    """metadata sem version, versão não semver, sources repetidas ou authored não booleano."""
    assert _erros("skill-frontmatter-v1.json", _skill(metadata=metadata))


def test_frontmatter_rejeita_sem_metadata() -> None:
    """metadata é obrigatória nas skills do praxisforge."""
    documento = _skill()
    del documento["metadata"]
    assert _erros("skill-frontmatter-v1.json", documento)


def _marcador(**campos: object) -> dict[str, object]:
    documento: dict[str, object] = {
        "schema_version": "1",
        "name": "revisar-codigo",
        "version": "1.0.0",
        "content_sha256": "a" * 64,
        "source": "skills/revisar-codigo",
    }
    documento.update(campos)
    return documento


def test_marcador_valido() -> None:
    """Marcador completo é aceito."""
    assert _erros("skill-publication-v1.json", _marcador()) == []


@pytest.mark.parametrize(
    "campos",
    [
        {"content_sha256": "a" * 63},
        {"content_sha256": "A" * 64},
        {"source": "/home/x/skills/revisar-codigo"},
        {"schema_version": "2"},
        {"extra": 1},
    ],
)
def test_marcador_rejeita_invalido(campos: dict[str, object]) -> None:
    """Hash fora do formato, source absoluto, versão de schema errada ou campo extra."""
    assert _erros("skill-publication-v1.json", _marcador(**campos))
