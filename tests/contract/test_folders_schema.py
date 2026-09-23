# -*- coding: utf-8 -*-
"""
NOME: test_folders_schema.py
TITULO: Testes de contrato — schemas/folders-schema-v1.json
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:04
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 22/09/2026 09:45: criação (T010)
    - 22/09/2026 17:34: +casos status "ignore" (T004, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:04: +last_curated_commit (T002, feature 004-deteccao-mudanca-conteudo)
STATUS: DEV
"""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

SCHEMA_PATH = Path(__file__).parents[2] / "schemas" / "folders-schema-v1.json"


@pytest.fixture
def schema() -> dict[str, object]:
    return cast(dict[str, object], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_schema_eh_um_metaschema_valido(schema: dict[str, object]) -> None:
    """O schema publicado é um Draft 2020-12 válido."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:  # pragma: no cover - falha esperada só em regressão
        pytest.fail(f"schema inválido: {error}")


def _validar(schema: dict[str, object], documento: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(documento)]


def test_registro_valido_nao_tem_erros(schema: dict[str, object]) -> None:
    """Um registro válido não levanta violações."""
    documento = {
        "schema_version": "1",
        "folders": {
            "github_forks": {
                "description": "Forks de repositórios de referência",
                "content_type": "repository_forks",
                "license": "unknown",
                "last_scanned": None,
                "status": "pending",
            }
        },
    }
    assert _validar(schema, documento) == []


@pytest.mark.parametrize(
    "documento",
    [
        {"folders": {}},  # sem schema_version
        {"schema_version": "2", "folders": {}},  # versão errada
        {
            "schema_version": "1",
            "folders": {"exemplo": {"description": "x", "content_type": "docs"}},
        },  # campo ausente (license, last_scanned, status)
        {
            "schema_version": "1",
            "folders": {
                "Exemplo": {
                    "description": "x",
                    "content_type": "docs",
                    "license": "MIT",
                    "last_scanned": None,
                    "status": "not_scanned",
                }
            },
        },  # alias maiúsculo
        {
            "schema_version": "1",
            "folders": {
                "/home/user/pasta": {
                    "description": "x",
                    "content_type": "docs",
                    "license": "MIT",
                    "last_scanned": None,
                    "status": "not_scanned",
                }
            },
        },  # alias que é caminho absoluto
        {
            "schema_version": "1",
            "folders": {
                "exemplo": {
                    "description": "x",
                    "content_type": "docs",
                    "license": "unknown",
                    "last_scanned": None,
                    "status": "scanned",
                }
            },
        },  # licença unknown com status != pending
        {
            "schema_version": "1",
            "folders": {
                "exemplo": {
                    "description": "x",
                    "content_type": "docs",
                    "license": "MIT",
                    "last_scanned": "2026-09-21T15:55:00-03:00",
                    "status": "not_scanned",
                }
            },
        },  # not_scanned com data
        {
            "schema_version": "1",
            "folders": {
                "exemplo": {
                    "description": "x",
                    "content_type": "docs",
                    "license": "MIT",
                    "last_scanned": None,
                    "status": "arquivada",
                }
            },
        },  # status fora do conjunto
        {
            "schema_version": "1",
            "folders": {
                "exemplo": {
                    "description": "x",
                    "content_type": "docs",
                    "license": "MIT",
                    "last_scanned": "ontem",
                    "status": "scanned",
                }
            },
        },  # last_scanned formato inválido
        {
            "schema_version": "1",
            "folders": {
                "exemplo": {
                    "description": "x",
                    "content_type": "docs",
                    "license": "MIT",
                    "last_scanned": "2026-13-40T00:00:00-03:00",
                    "status": "scanned",
                }
            },
        },  # last_scanned data impossível
    ],
)
def test_documentos_invalidos_sao_rejeitados(
    schema: dict[str, object], documento: dict[str, object]
) -> None:
    """Cada variação inválida da spec é rejeitada pelo schema."""
    assert _validar(schema, documento) != []


def test_status_ignore_eh_valido(schema: dict[str, object]) -> None:
    """status: 'ignore' é aceito pelo schema (feature 003, FR-010)."""
    documento = {
        "schema_version": "1",
        "folders": {
            "exemplo": {
                "description": "x",
                "content_type": "docs",
                "license": "MIT",
                "last_scanned": None,
                "status": "ignore",
            }
        },
    }
    assert _validar(schema, documento) == []


def test_licenca_unknown_com_status_ignore_eh_valido(schema: dict[str, object]) -> None:
    """license: 'unknown' + status: 'ignore' é aceito (invariante relaxada, FR-011)."""
    documento = {
        "schema_version": "1",
        "folders": {
            "exemplo": {
                "description": "x",
                "content_type": "docs",
                "license": "unknown",
                "last_scanned": None,
                "status": "ignore",
            }
        },
    }
    assert _validar(schema, documento) == []


def test_licenca_unknown_com_status_scanned_continua_invalido(schema: dict[str, object]) -> None:
    """Regressão: license: 'unknown' + status diferente de pending/ignore continua rejeitado."""
    documento = {
        "schema_version": "1",
        "folders": {
            "exemplo": {
                "description": "x",
                "content_type": "docs",
                "license": "unknown",
                "last_scanned": None,
                "status": "scanned",
            }
        },
    }
    assert _validar(schema, documento) != []


def _doc_com_commit(valor: object) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "folders": {
            "repo": {
                "description": "Repositório curado",
                "content_type": "repository_forks",
                "license": "MIT",
                "last_scanned": None,
                "status": "curated",
                "last_curated_commit": valor,
            }
        },
    }


@pytest.mark.parametrize("valor", ["a" * 40, "0123456789abcdef" * 4])
def test_last_curated_commit_sha1_e_sha256_sao_validos(
    schema: dict[str, object], valor: str
) -> None:
    """Hash de 40 (SHA-1) ou 64 (SHA-256) hex minúsculos é aceito (FR-011)."""
    assert _validar(schema, _doc_com_commit(valor)) == []


@pytest.mark.parametrize(
    "valor",
    ["A" * 40, "a" * 39, "a" * 41, "g" * 40, "a" * 63, "", None, 12345],
    ids=["maiusculo", "39", "41", "nao_hex", "63", "vazio", "null", "numero"],
)
def test_last_curated_commit_invalido_eh_rejeitado(
    schema: dict[str, object], valor: object
) -> None:
    """Hash fora do formato é rejeitado pelo contrato (FR-011)."""
    assert _validar(schema, _doc_com_commit(valor)) != []


def test_registro_versionado_atual_continua_valido(schema: dict[str, object]) -> None:
    """src/data/folders.yaml, sem o campo novo, continua válido (FR-012, SC-004)."""
    import yaml

    from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader

    texto = (Path(__file__).parents[2] / "src" / "data" / "folders.yaml").read_text("utf-8")
    documento = yaml.load(texto, Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
    assert _validar(schema, documento) == []
