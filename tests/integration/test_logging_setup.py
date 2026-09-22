# -*- coding: utf-8 -*-
"""
NOME: test_logging_setup.py
TITULO: Testes de falha — logs estruturados (Infrastructure)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:48
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.logging_setup
HISTÓRICO:
    - 22/09/2026 09:45: criação (T015)
STATUS: DEV
"""

import json
import logging

from praxisforge.infrastructure.logging_setup import configure_logging, log_event


def test_saida_em_json_com_campos_esperados(caplog: object) -> None:
    """log_event escreve um registro cujo JSON tem event, alias, outcome, error_type."""
    configure_logging()
    logger = logging.getLogger("praxisforge.test")
    with caplog.at_level(logging.INFO):  # type: ignore[attr-defined]
        log_event(
            logger,
            event="register_folder",
            alias="github_forks",
            outcome="ok",
            error_type=None,
        )
    assert caplog.records  # type: ignore[attr-defined]
    payload = json.loads(caplog.records[-1].message)  # type: ignore[attr-defined]
    assert payload["event"] == "register_folder"
    assert payload["alias"] == "github_forks"
    assert payload["outcome"] == "ok"
    assert payload["error_type"] is None


def test_nenhuma_linha_contem_caminho_absoluto_ou_segredo(caplog: object) -> None:
    """Nenhum log emitido carrega caminho absoluto ou segredo passado como extra."""
    configure_logging()
    logger = logging.getLogger("praxisforge.test")
    with caplog.at_level(logging.INFO):  # type: ignore[attr-defined]
        log_event(
            logger,
            event="resolve_path",
            alias="github_forks",
            outcome="falha",
            error_type="FolderPathInvalidError",
        )
    for record in caplog.records:  # type: ignore[attr-defined]
        assert "/home/" not in record.message
        assert "/Users/" not in record.message
