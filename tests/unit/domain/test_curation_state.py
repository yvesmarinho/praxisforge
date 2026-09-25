# -*- coding: utf-8 -*-
"""
NOME: test_curation_state.py
TITULO: Testes de falha — estado da curadoria: situação e reconciliação (feature 010)
DATA: 25/09/2026 15:00
MODIFICADO: 25/09/2026 14:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.curation_state
HISTÓRICO:
    - 25/09/2026 15:00: criação (T022, T027, feature 010)
STATUS: DEV
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.curation_artifact import Artifact, ArtifactKind, Manifest, Stage
from praxisforge.domain.curation_state import (
    ArtifactState,
    CurationState,
    Situation,
    reconcile,
    situation,
    stage_counts,
)
from praxisforge.domain.errors import InvalidCurationArtifactError

AGORA = datetime(2026, 9, 25, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
V1, V2 = "1" * 64, "2" * 64
H1, H2 = "a" * 64, "b" * 64


def _estado(artefatos: dict[str, ArtifactState], versao: str = V1) -> CurationState:
    return CurationState("demo_a", versao, AGORA, artefatos)


def _manifesto(*artefatos: Artifact, versao: str = V1) -> Manifest:
    return Manifest("demo_a", versao, artefatos, ())


def _art(path: str, sha: str = H1, kind: ArtifactKind = ArtifactKind.SKILL) -> Artifact:
    return Artifact(path, kind, 1, sha, 1)


def _st(stage: Stage, sha: str = H1, **extra: object) -> ArtifactState:
    return ArtifactState(ArtifactKind.SKILL, sha, stage, **extra)  # type: ignore[arg-type]


# --- invariantes -------------------------------------------------------------------


def test_estado_rejeita_attempts_negativo_e_sha_invalido() -> None:
    with pytest.raises(InvalidCurationArtifactError):
        _st(Stage.PENDING, attempts=-1)
    with pytest.raises(InvalidCurationArtifactError):
        _st(Stage.PENDING, sha="x")


def test_estado_rejeita_data_sem_fuso_e_path_absoluto() -> None:
    with pytest.raises(InvalidCurationArtifactError):
        CurationState("demo_a", V1, datetime(2026, 9, 25), {})  # noqa: DTZ001
    with pytest.raises(InvalidCurationArtifactError):
        _estado({"/abs": _st(Stage.PENDING)})


# --- situação (US2) ----------------------------------------------------------------


def test_sem_estado_nao_inventariada() -> None:
    assert situation(None) is Situation.NOT_INVENTORIED


def test_zero_artefatos_completa() -> None:
    assert situation(_estado({})) is Situation.COMPLETE


@pytest.mark.parametrize(
    ("estados", "esperado"),
    [
        ([_st(Stage.PROMOTED), _st(Stage.REMOVED), _st(Stage.DISCARDED)], Situation.COMPLETE),
        ([_st(Stage.PROMOTED), _st(Stage.FAILED)], Situation.INCOMPLETE),
        ([_st(Stage.REVIEWED)], Situation.INCOMPLETE),
        ([_st(Stage.REVIEWED, verdict="accepted")], Situation.COMPLETE),
        ([_st(Stage.PENDING)], Situation.INCOMPLETE),
    ],
)
def test_situacao(estados: list[ArtifactState], esperado: Situation) -> None:
    assert situation(_estado({f"a{i}": s for i, s in enumerate(estados)})) is esperado


def test_contagem_por_etapa_inclui_zeros() -> None:
    contagem = stage_counts(_estado({"a": _st(Stage.PENDING), "b": _st(Stage.PENDING)}))
    assert contagem[Stage.PENDING] == 2
    assert contagem[Stage.PROMOTED] == 0
    assert list(contagem) == list(Stage)


# --- reconciliação (US3) -----------------------------------------------------------


def test_primeiro_inventario_tudo_pendente() -> None:
    novo = reconcile(None, _manifesto(_art("a"), _art("b")), AGORA)
    assert {p: s.stage for p, s in novo.artifacts.items()} == {
        "a": Stage.PENDING,
        "b": Stage.PENDING,
    }
    assert novo.updated_at == AGORA
    assert novo.conventions_version == V1


def test_inalterado_mantem_etapa_veredito_e_tentativas() -> None:
    anterior = _estado({"a": _st(Stage.REVIEWED, verdict="accepted", attempts=2)})
    novo = reconcile(anterior, _manifesto(_art("a")), AGORA)
    assert novo.artifacts["a"] == anterior.artifacts["a"]


def test_hash_alterado_volta_para_pendente() -> None:
    anterior = _estado({"a": _st(Stage.PROMOTED, attempts=3, last_error="x", verdict="accepted")})
    novo = reconcile(anterior, _manifesto(_art("a", sha=H2)), AGORA).artifacts["a"]
    assert (novo.stage, novo.sha256, novo.verdict, novo.last_error) == (
        Stage.PENDING,
        H2,
        None,
        None,
    )
    assert novo.attempts == 3


def test_kind_alterado_por_convencoes_volta_para_pendente() -> None:
    """FR-016: convenções mudaram e o artefato foi reclassificado."""
    anterior = _estado({"a": _st(Stage.PROMOTED)})
    manifesto = _manifesto(_art("a", kind=ArtifactKind.AGENT), versao=V2)
    novo = reconcile(anterior, manifesto, AGORA)
    assert novo.artifacts["a"].stage is Stage.PENDING
    assert novo.artifacts["a"].kind is ArtifactKind.AGENT
    assert novo.conventions_version == V2


def test_convencoes_mudaram_mas_kind_igual_mantem() -> None:
    anterior = _estado({"a": _st(Stage.PROMOTED)})
    novo = reconcile(anterior, _manifesto(_art("a"), versao=V2), AGORA)
    assert novo.artifacts["a"].stage is Stage.PROMOTED


def test_sumido_vira_removido_e_fica_no_estado() -> None:
    anterior = _estado({"a": _st(Stage.PROMOTED), "b": _st(Stage.PENDING)})
    novo = reconcile(anterior, _manifesto(_art("a")), AGORA)
    assert novo.artifacts["b"].stage is Stage.REMOVED
    assert novo.artifacts["b"].sha256 == H1


def test_removido_que_reaparece_volta_para_pendente() -> None:
    anterior = _estado({"a": _st(Stage.REMOVED)})
    assert reconcile(anterior, _manifesto(_art("a")), AGORA).artifacts["a"].stage is Stage.PENDING


def test_alias_diferente_recusado() -> None:
    anterior = CurationState("outro_b", V1, AGORA, {})
    with pytest.raises(InvalidCurationArtifactError):
        reconcile(anterior, _manifesto(), AGORA)
