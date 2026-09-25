# -*- coding: utf-8 -*-
"""
NOME: test_json_curation_store.py
TITULO: Testes de falha — manifesto e estado da curadoria fora do repositório (feature 010)
DATA: 25/09/2026 15:02
MODIFICADO: 25/09/2026 14:53
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.json_curation_store
HISTÓRICO:
    - 25/09/2026 15:02: criação (T013, feature 010)
STATUS: DEV
"""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.curation_artifact import (
    Artifact,
    ArtifactKind,
    ExcludedEntry,
    ExclusionReason,
    Manifest,
    Stage,
)
from praxisforge.domain.curation_state import ArtifactState, CurationState, reconcile
from praxisforge.domain.errors import (
    CurationLockedError,
    CurationStateCorruptError,
    CurationStorageError,
)
from praxisforge.infrastructure.json_curation_store import JsonCurationStore
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator

ROOT = Path(__file__).parents[2]
AGORA = datetime(2026, 9, 25, 15, 2, tzinfo=ZoneInfo("America/Sao_Paulo"))
V = "c" * 64


def _store(base: Path) -> JsonCurationStore:
    return JsonCurationStore(base, JsonSchemaContractValidator(schemas_dir=ROOT / "schemas"))


def _manifesto() -> Manifest:
    return Manifest(
        "demo_a",
        V,
        (
            Artifact("z.md", ArtifactKind.UNKNOWN, 1, "a" * 64, 1),
            Artifact("skills/x", ArtifactKind.SKILL, 3, "b" * 64, 2),
        ),
        (ExcludedEntry("node_modules", ExclusionReason.FIXED_DIR, True),),
    )


def test_ida_e_volta(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.load_state("demo_a") is None
    estado = reconcile(None, _manifesto(), AGORA)
    store.save(_manifesto(), estado)
    assert store.load_state("demo_a") == estado
    assert (tmp_path / "demo_a" / "manifest.json").is_file()


def test_manifesto_deterministico_e_ordenado(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(_manifesto(), reconcile(None, _manifesto(), AGORA))
    primeiro = (tmp_path / "demo_a" / "manifest.json").read_bytes()
    store.save(_manifesto(), reconcile(None, _manifesto(), AGORA))
    assert (tmp_path / "demo_a" / "manifest.json").read_bytes() == primeiro
    doc = json.loads(primeiro)
    assert [a["path"] for a in doc["artifacts"]] == ["skills/x", "z.md"]
    assert "updated_at" not in doc


@pytest.mark.parametrize(
    "conteudo",
    ["{", "[]", '{"schema_version": "9"}', '{"schema_version": "1", "alias": "demo_a"}'],
)
def test_estado_corrompido_recusado_sem_sobrescrever(tmp_path: Path, conteudo: str) -> None:
    arquivo = tmp_path / "demo_a" / "state.json"
    arquivo.parent.mkdir()
    arquivo.write_text(conteudo, encoding="utf-8")
    with pytest.raises(CurationStateCorruptError):
        _store(tmp_path).load_state("demo_a")
    assert arquivo.read_text(encoding="utf-8") == conteudo


def test_estado_de_outro_alias_recusado(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(_manifesto(), reconcile(None, _manifesto(), AGORA))
    (tmp_path / "outro_b").mkdir()
    (tmp_path / "demo_a" / "state.json").rename(tmp_path / "outro_b" / "state.json")
    with pytest.raises(CurationStateCorruptError):
        store.load_state("outro_b")


def test_estado_invalido_nao_e_gravado(tmp_path: Path) -> None:
    """FR-012: validação também ao gravar (alias fora do contrato)."""
    estado = CurationState("X", V, AGORA, {})
    with pytest.raises(CurationStorageError):
        _store(tmp_path).save(Manifest("X", V, (), ()), estado)
    assert not (tmp_path / "X" / "state.json").exists()


def test_falha_no_replace_mantem_anterior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path)
    estado = reconcile(None, _manifesto(), AGORA)
    store.save(_manifesto(), estado)
    antes = (tmp_path / "demo_a" / "state.json").read_bytes()

    def _falhar(*_: object) -> None:
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", _falhar)
    novo = CurationState(
        "demo_a", V, AGORA, {"z.md": ArtifactState(ArtifactKind.UNKNOWN, "d" * 64, Stage.FAILED)}
    )
    with pytest.raises(CurationStorageError):
        store.save(_manifesto(), novo)
    assert (tmp_path / "demo_a" / "state.json").read_bytes() == antes
    assert [p.name for p in (tmp_path / "demo_a").iterdir() if p.name.startswith(".tmp")] == []


def test_lock_impede_segunda_execucao(tmp_path: Path) -> None:
    store, outro = _store(tmp_path), _store(tmp_path)
    with store.lock("demo_a"):
        with pytest.raises(CurationLockedError), outro.lock("demo_a"):
            pass  # pragma: no cover
        with outro.lock("outro_b"):
            pass
    with outro.lock("demo_a"):
        pass


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignora permissões")
def test_diretorio_sem_permissao(tmp_path: Path) -> None:
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(CurationStorageError), _store(tmp_path / "curation").lock("demo_a"):
            pass  # pragma: no cover
    finally:
        tmp_path.chmod(0o700)
