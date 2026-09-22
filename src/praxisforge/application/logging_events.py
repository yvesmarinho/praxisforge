# -*- coding: utf-8 -*-
"""
NOME: logging_events.py
TITULO: Emissão de eventos estruturados em JSON — versão da Application (sem infra)
DATA: 22/09/2026 10:05
MODIFICADO: 22/09/2026 09:57
VERSÃO: 0.1.0
DEPEND: (stdlib logging/json apenas — Application não pode importar Infrastructure)
HISTÓRICO:
    - 22/09/2026 10:05: criação — corrige violação de camada revelada por
      tests/architecture/test_layer_rules.py (Application importava
      praxisforge.infrastructure.logging_setup)
STATUS: DEV
"""

import json
import logging


def log_event(
    logger: logging.Logger,
    event: str,
    alias: str,
    outcome: str,
    error_type: str | None,
) -> None:
    """
    Emite um evento estruturado em JSON, sem caminho absoluto nem segredo.

    Mesma forma de `infrastructure.logging_setup.log_event`; duplicada aqui
    (função pequena, só stdlib) para que a Application não dependa da
    Infrastructure — o handler/formatter fica configurado pela Infrastructure
    e é composto só em `presentation/cli.py`.

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
