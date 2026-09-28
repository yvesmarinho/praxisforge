# -*- coding: utf-8 -*-
"""
NOME: test_json_draft_store.py
TITULO: Testes de falha — área global de rascunhos curation/_drafts/ (feature 011)
DATA: 28/09/2026 16:16
MODIFICADO: 28/09/2026 16:16
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.json_draft_store
HISTÓRICO:
    - 28/09/2026 16:16: criação (T035, feature 011)
STATUS: DEV
"""

import stat
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.curation_draft import Draft, DraftOrigin, DraftProposal, draft_id_for
from praxisforge.domain.errors import (
    CurationLockedError,
    CurationPathUnsafeError,
    DraftStoreCorruptError,
)
from praxisforge.domain.structure_similarity import SimilarityCheck
from praxisforge.infrastructure.json_draft_store import JsonDraftStore
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator

ROOT = Path(__file__).parents[2]
AGORA = datetime(2026, 9, 28, 16, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
SHA = "a" * 64


def _store(base: Path) -> JsonDraftStore:
    return JsonDraftStore(base, JsonSchemaContractValidator(schemas_dir=ROOT / "schemas"))


def _rascunho(alias: str = "demo_a", path: str = "skills/x", alerta: bool = False) -> Draft:
    return Draft(
        draft_id=draft_id_for(alias, path),
        proposal=DraftProposal(ArtifactKind.RULE, "estilo-de-codigo", "Estilo.", "# Estilo\n"),
        origins=(DraftOrigin(alias, path, SHA),),
        checks=(SimilarityCheck(0.9 if alerta else 0.1, 0.7, False, "ok"),),
        merge_target=None,
        prompt_fingerprint="f" * 64,
        model="claude-sonnet-5",
        cost_usd=Decimal("0.02"),
        updated_at=AGORA,
    )


def test_ida_e_volta_e_ordem(tmp_path: Path) -> None:
    store = _store(tmp_path / "curation")
    assert store.list_pending() == []
    b, a = _rascunho(path="b.md"), _rascunho(path="a.md")
    with store.lock():
        store.save(b)
        store.save(a)
    ids = [d.draft_id for d in store.list_pending()]
    assert ids == sorted([a.draft_id, b.draft_id])
    assert store.load(a.draft_id) == a
    assert store.load("0" * 16) is None


def test_alertas_por_alias(tmp_path: Path) -> None:
    store = _store(tmp_path / "curation")
    with store.lock():
        store.save(_rascunho(path="a.md", alerta=True))
        store.save(_rascunho(path="b.md"))
        store.save(_rascunho(alias="demo_b", alerta=True))
    assert store.alerts_for("demo_a") == 1
    assert store.alerts_for("demo_b") == 1
    assert store.alerts_for("outra") == 0


def test_lock_exclusivo(tmp_path: Path) -> None:
    store = _store(tmp_path / "curation")
    with store.lock(), pytest.raises(CurationLockedError), _store(tmp_path / "curation").lock():
        pass


@pytest.mark.parametrize("conteudo", ["{", '{"schema_version": "1"}', "[]"])
def test_rascunho_corrompido(tmp_path: Path, conteudo: str) -> None:
    store = _store(tmp_path / "curation")
    with store.lock():
        store.save(_rascunho())
    arquivo = tmp_path / "curation" / "_drafts" / f"{_rascunho().draft_id}.json"
    arquivo.write_text(conteudo, encoding="utf-8")
    with pytest.raises(DraftStoreCorruptError, match=_rascunho().draft_id):
        store.list_pending()


def test_arquivo_com_nome_estranho_e_corrupcao(tmp_path: Path) -> None:
    store = _store(tmp_path / "curation")
    pasta = tmp_path / "curation" / "_drafts"
    pasta.mkdir(parents=True)
    (pasta / "nao-e-um-id.json").write_text("{}", encoding="utf-8")
    with pytest.raises(DraftStoreCorruptError, match="nao-e-um-id"):
        store.list_pending()


def test_permissoes(tmp_path: Path) -> None:
    store = _store(tmp_path / "curation")
    with store.lock():
        store.save(_rascunho())
    pasta = tmp_path / "curation" / "_drafts"
    assert stat.S_IMODE(pasta.stat().st_mode) == 0o700
    for arquivo in pasta.iterdir():
        assert stat.S_IMODE(arquivo.stat().st_mode) == 0o600


def test_link_simbolico(tmp_path: Path) -> None:
    base = tmp_path / "curation"
    base.mkdir()
    fora = tmp_path / "fora"
    fora.mkdir()
    (base / "_drafts").symlink_to(fora)
    store = _store(base)
    with pytest.raises(CurationPathUnsafeError):
        store.list_pending()
    with pytest.raises(CurationPathUnsafeError), store.lock():
        store.save(_rascunho())
    assert list(fora.iterdir()) == []
