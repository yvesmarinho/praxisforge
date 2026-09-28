# -*- coding: utf-8 -*-
"""
NOME: query_curation.py
TITULO: Caso de uso — status da curadoria por pasta (situação, contagem por etapa, falhas)
DATA: 25/09/2026 15:06
MODIFICADO: 28/09/2026 16:04
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 25/09/2026 15:06: criação (T025, feature 010) — faz test_query_curation.py passar
    - 28/09/2026 15:08: cabeçalho — horários adiantados ajustados ao commit (33d627d/8a7182f)
    - 28/09/2026 16:04: contagem por veredito da triagem e alertas de similaridade (T031, 011)
STATUS: DEV
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from praxisforge.application.ports import CurationStore, FolderRegistryRepository
from praxisforge.domain.curation_artifact import Stage
from praxisforge.domain.curation_state import Situation, situation, stage_counts
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.curation_triage import TriageVerdict
from praxisforge.domain.errors import CurationStateCorruptError
from praxisforge.domain.folder import Folder

# Reexportados para a Presentation (guarda AST: CLI não importa o domínio)
__all__ = ["CurationReport", "Situation", "Stage", "curation_status"]


@dataclass(frozen=True)
class CurationReport:
    """
    Situação da curadoria de uma pasta.

    `situation` é None e `error` traz o motivo quando o estado está corrompido.
    """

    alias: str
    situation: Situation | None
    counts: dict[Stage, int] = field(default_factory=dict)
    failures: list[tuple[str, str]] = field(default_factory=list)
    error: str | None = None
    verdicts: dict[str, int] = field(default_factory=dict)
    similarity_alerts: int = 0


def _relatorio(
    folder: Folder, store: CurationStore, alerts: Callable[[str], int] | None
) -> CurationReport:
    alias = folder.alias.value
    try:
        estado = store.load_state(alias)
    except CurationStateCorruptError as error:
        return CurationReport(alias=alias, situation=None, error=str(error))
    if estado is None:
        return CurationReport(alias=alias, situation=Situation.NOT_INVENTORIED)
    falhas = [
        (path, s.last_error or "")
        for path, s in estado.artifacts.items()
        if s.stage is Stage.FAILED
    ]
    vereditos = {v.value: 0 for v in TriageVerdict}
    for s in estado.artifacts.values():
        if s.triage is not None and s.stage is not Stage.REMOVED:
            vereditos[s.triage.verdict.value] += 1
    return CurationReport(
        alias=alias,
        situation=situation(estado),
        counts=stage_counts(estado),
        failures=falhas,
        verdicts=vereditos,
        similarity_alerts=alerts(alias) if alerts is not None else 0,
    )


def curation_status(
    repository: FolderRegistryRepository,
    store: CurationStore,
    alias: str | None = None,
    alerts: Callable[[str], int] | None = None,
) -> list[CurationReport]:
    """
    Status de uma pasta ou de todas (exceto `ignore`) — FR-017 a FR-019.

    :param repository: registro de pastas.
    :type repository: FolderRegistryRepository
    :param store: persistência do estado de curadoria.
    :type store: CurationStore
    :param alias: alias específico (None = todas).
    :type alias: str | None
    :param alerts: rascunhos com alerta de similaridade por alias (feature 011).
    :type alerts: Callable[[str], int] | None
    :return: um relatório por pasta, na ordem do registro.
    :rtype: list[CurationReport]
    :raises FolderNotFoundError: alias não registrado.
    """
    registry = repository.load()
    if alias is not None:
        return [_relatorio(registry.get(alias), store, alerts)]
    return [
        _relatorio(folder, store, alerts)
        for folder in registry.list()
        if folder.status is not CurationStatus.IGNORE
    ]
