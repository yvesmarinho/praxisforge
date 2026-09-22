# -*- coding: utf-8 -*-
"""
NOME: test_no_absolute_paths.py
TITULO: Testes de contrato — nenhum caminho absoluto pessoal versionado (SC-005)
DATA: 22/09/2026 10:10
MODIFICADO: 22/09/2026 10:01
VERSÃO: 0.1.0
DEPEND: pytest, jsonschema
HISTÓRICO:
    - 22/09/2026 10:10: criação (T044)
STATUS: DEV
"""

import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).parents[2]
_PATTERN = re.compile(r"/home/|/Users/|C:\\")


def test_nenhum_caminho_absoluto_pessoal_em_src_schemas() -> None:
    """src/ e schemas/ não contêm caminhos pessoais absolutos versionados."""
    ofensores = []
    for base in (ROOT / "src", ROOT / "schemas"):
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            try:
                conteudo = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if _PATTERN.search(conteudo):
                ofensores.append(str(path.relative_to(ROOT)))
    assert ofensores == []


def test_registro_com_caminho_absoluto_no_lugar_do_alias_eh_rejeitado() -> None:
    """Um registro com caminho absoluto como chave de alias é rejeitado pelo schema."""
    import json

    schema = json.loads((ROOT / "schemas" / "folders-schema-v1.json").read_text(encoding="utf-8"))
    documento = {
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
    }
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    erros = list(validator.iter_errors(documento))
    assert erros != []
