# -*- coding: utf-8 -*-
"""
NOME: test_folders_example.py
TITULO: Testes de contrato — registro de exemplo versionado e registro real fora do git
DATA: 24/09/2026 14:32
MODIFICADO: 24/09/2026 14:32
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema, pyyaml
HISTÓRICO:
    - 24/09/2026 14:32: criação (T013, US1, feature 007)
STATUS: DEV
"""

import json
import re
from pathlib import Path
from typing import cast

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader

ROOT = Path(__file__).parents[2]
EXEMPLO = ROOT / "src" / "data" / "folders.example.yaml"
_PESSOAL = re.compile(r"/home/|/Users/|C:\\")


def _exemplo() -> dict[str, object]:
    conteudo = EXEMPLO.read_text(encoding="utf-8")
    documento = yaml.load(conteudo, Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
    return cast(dict[str, object], documento)


def test_exemplo_existe_e_eh_valido_no_schema_v2() -> None:
    """src/data/folders.example.yaml valida em folders-schema-v2 (FR-006, FR-007)."""
    schema = json.loads((ROOT / "schemas" / "folders-schema-v2.json").read_text(encoding="utf-8"))
    erros = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(_exemplo())
    )
    assert erros == []


def test_exemplo_tem_ao_menos_tres_pastas_sem_caminho_pessoal() -> None:
    """Pastas fictícias sob caminhos genéricos (FR-006)."""
    pastas = cast(dict[str, dict[str, object]], _exemplo()["folders"])
    assert len(pastas) >= 3
    for pasta in pastas.values():
        assert not _PESSOAL.search(str(pasta["path"]))


def test_registro_real_esta_no_gitignore() -> None:
    """src/data/folders.yaml não é versionado (FR-005)."""
    linhas = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "src/data/folders.yaml" in [linha.strip() for linha in linhas]
