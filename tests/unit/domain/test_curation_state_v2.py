# -*- coding: utf-8 -*-
"""
NOME: test_curation_state_v2.py
TITULO: Testes de falha — estado v2: triagem preservada ou zerada na reconciliação (feature 011)
DATA: 28/09/2026 15:52
MODIFICADO: 28/09/2026 15:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.curation_state
HISTÓRICO:
    - 28/09/2026 15:52: criação (T008, feature 011)
STATUS: DEV
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from praxisforge.domain.curation_artifact import Artifact, ArtifactKind, Manifest, Stage
from praxisforge.domain.curation_state import ArtifactState, CurationState, reconcile
from praxisforge.domain.curation_triage import Triage, TriageVerdict

AGORA = datetime(2026, 9, 28, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
A, B = "a" * 64, "b" * 64
CONV = "c" * 64

TRIAGEM = Triage(
    verdict=TriageVerdict.OUT_OF_SCOPE,
    justification="changelog",
    covered_by=(),
    merge_target=None,
    suggested_kind=None,
    ideas_summary=None,
    prompt_fingerprint="f" * 64,
    model="claude-haiku-4-5",
    cost_usd=Decimal("0"),
    triaged_at=AGORA,
)


def _manifesto(**hashes: str) -> Manifest:
    artefatos = tuple(
        Artifact(path=f"{nome}.md", kind=ArtifactKind.UNKNOWN, size=1, sha256=h, files=1)
        for nome, h in hashes.items()
    )
    return Manifest(alias="demo_a", conventions_version=CONV, artifacts=artefatos, excluded=())


def _anterior() -> CurationState:
    triado = ArtifactState(ArtifactKind.UNKNOWN, A, Stage.TRIAGED, triage=TRIAGEM)
    return CurationState("demo_a", CONV, AGORA, {"x.md": triado, "y.md": triado})


def test_sem_triagem_por_padrao() -> None:
    assert ArtifactState(ArtifactKind.SKILL, A, Stage.PENDING).triage is None


def test_reconcile_preserva_triagem_do_inalterado_e_zera_do_alterado() -> None:
    novo = reconcile(_anterior(), _manifesto(x=A, y=B, z=A), AGORA)
    assert novo.artifacts["x.md"].triage == TRIAGEM
    assert novo.artifacts["x.md"].stage is Stage.TRIAGED
    assert novo.artifacts["y.md"].triage is None
    assert novo.artifacts["y.md"].stage is Stage.PENDING
    assert novo.artifacts["z.md"].triage is None


def test_reconcile_removido_que_reaparece_perde_triagem() -> None:
    sumiu = reconcile(_anterior(), _manifesto(y=A), AGORA)
    assert sumiu.artifacts["x.md"].stage is Stage.REMOVED
    voltou = reconcile(sumiu, _manifesto(x=A, y=A), AGORA)
    assert voltou.artifacts["x.md"].stage is Stage.PENDING
    assert voltou.artifacts["x.md"].triage is None
