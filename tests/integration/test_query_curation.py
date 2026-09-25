# -*- coding: utf-8 -*-
"""
NOME: test_query_curation.py
TITULO: Testes de falha — status da curadoria por pasta (feature 010)
DATA: 25/09/2026 15:20
MODIFICADO: 25/09/2026 14:56
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.query_curation
HISTÓRICO:
    - 25/09/2026 15:20: criação (T023, feature 010)
STATUS: DEV
"""

import json
from pathlib import Path

import pytest

from praxisforge.application.query_curation import curation_status
from praxisforge.domain.curation_artifact import Stage
from praxisforge.domain.curation_state import Situation
from praxisforge.domain.errors import FolderNotFoundError
from praxisforge.infrastructure.yaml_folder_registry import YamlFolderRegistryRepository
from tests.integration.test_inventory_folders import _VALIDATOR, _Ambiente


@pytest.fixture
def amb(tmp_path: Path) -> _Ambiente:
    return _Ambiente(tmp_path)


def _status(amb: _Ambiente, alias: str | None = None):  # type: ignore[no-untyped-def]
    return curation_status(YamlFolderRegistryRepository(amb.registry, _VALIDATOR), amb.store, alias)


def test_inventariada_incompleta_com_contagem(amb: _Ambiente) -> None:
    amb.registrar("demo_a", {"README.md": "a", "CLAUDE.md": "b"})
    amb.inventariar("demo_a")
    (relatorio,) = _status(amb, "demo_a")
    assert relatorio.situation is Situation.INCOMPLETE
    assert relatorio.counts[Stage.PENDING] == 2
    assert relatorio.error is None


def test_curada_sem_inventario(amb: _Ambiente) -> None:
    """FR-019: curadoria legada aparece como sem inventário."""
    amb.registrar("legada_a", {"README.md": "a"}, status="curated")
    (relatorio,) = _status(amb)
    assert relatorio.situation is Situation.NOT_INVENTORIED
    assert relatorio.counts == {}


def test_completa_e_falhas(amb: _Ambiente) -> None:
    amb.registrar("demo_a", {"README.md": "a", "CLAUDE.md": "b"})
    amb.inventariar("demo_a")
    arquivo = amb.store_dir("demo_a") / "state.json"
    doc = json.loads(arquivo.read_text("utf-8"))
    doc["artifacts"]["README.md"].update(stage="failed", last_error="timeout", attempts=1)
    doc["artifacts"]["CLAUDE.md"]["stage"] = "promoted"
    arquivo.write_text(json.dumps(doc), encoding="utf-8")
    (relatorio,) = _status(amb, "demo_a")
    assert relatorio.situation is Situation.INCOMPLETE
    assert relatorio.failures == [("README.md", "timeout")]
    doc["artifacts"]["README.md"]["stage"] = "discarded"
    arquivo.write_text(json.dumps(doc), encoding="utf-8")
    assert _status(amb, "demo_a")[0].situation is Situation.COMPLETE


def test_estado_corrompido_nao_impede_as_outras(amb: _Ambiente) -> None:
    amb.registrar("boa_a", {"README.md": "a"})
    amb.registrar("ruim_b", {"README.md": "b"})
    amb.registrar("fora_c", {}, status="ignore")
    amb.inventariar("boa_a")
    amb.store_dir("ruim_b").mkdir(parents=True)
    (amb.store_dir("ruim_b") / "state.json").write_text("{", encoding="utf-8")
    relatorios = {r.alias: r for r in _status(amb)}
    assert set(relatorios) == {"boa_a", "ruim_b"}
    assert relatorios["boa_a"].error is None
    assert relatorios["ruim_b"].situation is None
    assert relatorios["ruim_b"].error is not None


def test_alias_inexistente(amb: _Ambiente) -> None:
    amb.registrar("demo_a", {})
    with pytest.raises(FolderNotFoundError):
        _status(amb, "nao_existe")
