# -*- coding: utf-8 -*-
"""
NOME: test_json_curation_store_v2.py
TITULO: Testes de falha — store de curadoria v2: leitura de v1, save_state, permissões, links
DATA: 28/09/2026 15:52
MODIFICADO: 28/09/2026 15:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.json_curation_store
HISTÓRICO:
    - 28/09/2026 15:52: criação (T009, feature 011)
STATUS: DEV
"""

import json
import stat
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.curation_artifact import Artifact, ArtifactKind, Manifest, Stage
from praxisforge.domain.curation_state import CurationState, reconcile
from praxisforge.domain.curation_triage import MergeTarget, Triage, TriageVerdict, with_triage
from praxisforge.domain.errors import CurationPathUnsafeError, CurationStateCorruptError
from praxisforge.infrastructure.json_curation_store import JsonCurationStore
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator

ROOT = Path(__file__).parents[2]
AGORA = datetime(2026, 9, 28, 15, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
V = "c" * 64


def _store(base: Path) -> JsonCurationStore:
    return JsonCurationStore(base, JsonSchemaContractValidator(schemas_dir=ROOT / "schemas"))


def _manifesto() -> Manifest:
    return Manifest("demo_a", V, (Artifact("skills/x", ArtifactKind.SKILL, 3, "b" * 64, 2),), ())


def _triage() -> Triage:
    return Triage(
        verdict=TriageVerdict.GAP,
        justification="ideia nova",
        covered_by=(),
        merge_target=MergeTarget("library", "skill/diretrizes-codificacao"),
        suggested_kind=None,
        ideas_summary="resumo",
        prompt_fingerprint="f" * 64,
        model="claude-haiku-4-5",
        cost_usd=Decimal("0.0051"),
        triaged_at=AGORA,
    )


def _estado_triado() -> CurationState:
    base = reconcile(None, _manifesto(), AGORA)
    triado = with_triage(base.artifacts["skills/x"], _triage())
    return CurationState("demo_a", V, AGORA, {"skills/x": triado})


def test_grava_v2_e_le_triagem(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(_manifesto(), _estado_triado())
    documento = json.loads((tmp_path / "demo_a" / "state.json").read_text(encoding="utf-8"))
    assert documento["schema_version"] == "2"
    lido = store.load_state("demo_a")
    assert lido == _estado_triado()
    assert lido is not None and lido.artifacts["skills/x"].triage == _triage()


def test_le_estado_v1_sem_triagem(tmp_path: Path) -> None:
    (tmp_path / "demo_a").mkdir()
    v1 = {
        "schema_version": "1",
        "alias": "demo_a",
        "conventions_version": V,
        "updated_at": "2026-09-25T15:00:00-03:00",
        "artifacts": {
            "skills/x": {
                "kind": "skill",
                "sha256": "b" * 64,
                "stage": "pending",
                "verdict": None,
                "last_error": None,
                "attempts": 0,
            }
        },
    }
    (tmp_path / "demo_a" / "state.json").write_text(json.dumps(v1), encoding="utf-8")
    lido = _store(tmp_path).load_state("demo_a")
    assert lido is not None
    assert lido.artifacts["skills/x"].stage is Stage.PENDING
    assert lido.artifacts["skills/x"].triage is None


def test_versao_desconhecida(tmp_path: Path) -> None:
    (tmp_path / "demo_a").mkdir()
    (tmp_path / "demo_a" / "state.json").write_text(
        json.dumps({"schema_version": "9", "alias": "demo_a"}), encoding="utf-8"
    )
    with pytest.raises(CurationStateCorruptError):
        _store(tmp_path).load_state("demo_a")


def test_save_state_sem_manifesto(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(_manifesto(), reconcile(None, _manifesto(), AGORA))
    manifesto_antes = (tmp_path / "demo_a" / "manifest.json").read_bytes()
    store.save_state(_estado_triado())
    assert (tmp_path / "demo_a" / "manifest.json").read_bytes() == manifesto_antes
    assert store.load_state("demo_a") == _estado_triado()


def test_permissoes(tmp_path: Path) -> None:
    base = tmp_path / "curation"
    store = _store(base)
    store.save(_manifesto(), _estado_triado())
    for caminho in (base, base / "demo_a"):
        assert stat.S_IMODE(caminho.stat().st_mode) == 0o700
    for nome in ("state.json", "manifest.json"):
        assert stat.S_IMODE((base / "demo_a" / nome).stat().st_mode) == 0o600


def test_link_simbolico_no_diretorio_do_alias(tmp_path: Path) -> None:
    base = tmp_path / "curation"
    base.mkdir()
    fora = tmp_path / "fora"
    fora.mkdir()
    (base / "demo_a").symlink_to(fora)
    with pytest.raises(CurationPathUnsafeError):
        _store(base).save_state(_estado_triado())
    assert list(fora.iterdir()) == []


def test_link_simbolico_no_arquivo_de_estado(tmp_path: Path) -> None:
    base = tmp_path / "curation"
    (base / "demo_a").mkdir(parents=True)
    alvo = tmp_path / "alvo.json"
    alvo.write_text("{}", encoding="utf-8")
    (base / "demo_a" / "state.json").symlink_to(alvo)
    with pytest.raises(CurationPathUnsafeError):
        _store(base).save_state(_estado_triado())
    with pytest.raises(CurationPathUnsafeError):
        _store(base).load_state("demo_a")
    assert alvo.read_text(encoding="utf-8") == "{}"


def test_base_como_link_simbolico(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    base = tmp_path / "curation"
    base.symlink_to(real)
    with pytest.raises(CurationPathUnsafeError):
        _store(base).save_state(_estado_triado())
