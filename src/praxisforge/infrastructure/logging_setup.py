# -*- coding: utf-8 -*-
"""
NOME: logging_setup.py
TITULO: Logs estruturados em JSON — configuração e emissão de eventos
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:50
VERSÃO: 0.1.0
DEPEND: (stdlib logging apenas)
HISTÓRICO:
    - 22/09/2026 09:45: criação (T026) — faz tests/integration/test_logging_setup.py passar
STATUS: DEV
"""

import json
import logging


class _JsonPassthroughFormatter(logging.Formatter):
    """Formatter que repassa `record.getMessage()` (já um JSON), sem prefixos."""

    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configura o logging raiz com um formatter que passa através mensagens JSON.

    Idempotente: se já houver handlers configurados, não reconfigura.

    :param level: nível mínimo de log.
    :type level: int
    """
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonPassthroughFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def log_event(
    logger: logging.Logger,
    event: str,
    alias: str,
    outcome: str,
    error_type: str | None,
) -> None:
    """
    Emite um evento estruturado em JSON, sem caminho absoluto nem segredo.

    :param logger: logger da fronteira que emite o evento.
    :type logger: logging.Logger
    :param event: nome do evento (ex.: `"register_folder"`).
    :type event: str
    :param alias: alias envolvido na operação.
    :type alias: str
    :param outcome: resultado (`"ok"`, `"falha"`, `"inalterado"`, ...).
    :type outcome: str
    :param error_type: nome da exceção semântica, se houve falha; None caso contrário.
    :type error_type: str | None
    """
    payload = {
        "event": event,
        "alias": alias,
        "outcome": outcome,
        "error_type": error_type,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
