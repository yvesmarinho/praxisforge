# -*- coding: utf-8 -*-
"""
NOME: test_cli_curation.py
TITULO: Testes de falha — CLI praxisforge curation inventory|status (feature 010)
DATA: 25/09/2026 15:23
MODIFICADO: 25/09/2026 14:57
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 25/09/2026 15:23: criação (T021, T026, T032, feature 010)
STATUS: DEV
"""

import json
import shutil
from pathlib import Path

import pytest

from praxisforge.infrastructure.json_curation_store import JsonCurationStore
from praxisforge.presentation.cli import main
from tests.integration.test_inventory_folders import _VALIDATOR, _Ambiente


@pytest.fixture
def amb(tmp_path: Path) -> _Ambiente:
    return _Ambiente(tmp_path)


def _run(amb: _Ambiente, capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(["--registry", str(amb.registry), "curation", *argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- inventory (US1, US4) ----------------------------------------------------------


def test_inventory_sucesso(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    pasta = amb.registrar("demo_a", {"README.md": "a", "app.py": "x"})
    capsys.readouterr()
    code, out, _ = _run(amb, capsys, "inventory", "demo_a")
    assert code == 0
    assert "demo_a: 1 artefatos (1 pendentes, 0 removidos), 1 excluídos — incompleta" in out
    assert str(pasta) not in out


def test_inventory_sem_alvo_e_alvo_duplo(
    amb: _Ambiente, capsys: pytest.CaptureFixture[str]
) -> None:
    amb.registrar("demo_a", {})
    assert _run(amb, capsys, "inventory")[0] == 2
    assert _run(amb, capsys, "inventory", "demo_a", "--all")[0] == 2


def test_inventory_alias_inexistente(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {})
    code, _, err = _run(amb, capsys, "inventory", "nao_existe")
    assert code == 1
    assert "nao_existe" in err


def test_inventory_sem_convencoes(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {})
    (amb.registry.parent / "curation-conventions.yaml").unlink()
    code, _, err = _run(amb, capsys, "inventory", "demo_a")
    assert code == 3
    assert "cp src/data/curation-conventions.example.yaml" in err


def test_inventory_convencoes_invalidas(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {})
    (amb.registry.parent / "curation-conventions.yaml").write_text("rules: [", encoding="utf-8")
    assert _run(amb, capsys, "inventory", "demo_a")[0] == 1


def test_inventory_lock_ocupado(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {})
    with JsonCurationStore(amb.registry.parent / "curation", _VALIDATOR).lock("demo_a"):
        code, _, err = _run(amb, capsys, "inventory", "demo_a")
    assert code == 3
    assert "em execução" in err


def test_inventory_estado_corrompido(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {})
    amb.store_dir("demo_a").mkdir(parents=True)
    (amb.store_dir("demo_a") / "state.json").write_text("{", encoding="utf-8")
    assert _run(amb, capsys, "inventory", "demo_a")[0] == 1


def test_inventory_pasta_inacessivel(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    shutil.rmtree(amb.registrar("demo_a", {}))
    assert _run(amb, capsys, "inventory", "demo_a")[0] == 3


def test_inventory_all(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("ok_a", {"README.md": "a"})
    shutil.rmtree(amb.registrar("sumida_b", {}))
    amb.registrar("fora_c", {}, status="ignore")
    code, out, _ = _run(amb, capsys, "inventory", "--all")
    assert code == 1
    assert "ok_a: 1 artefatos" in out
    assert "sumida_b: FALHA" in out
    assert "Resumo: 1 inventariadas, 1 falharam, 1 puladas (ignore)" in out


def test_inventory_all_ok(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("ok_a", {})
    assert _run(amb, capsys, "inventory", "--all")[0] == 0


def test_registro_ausente(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    code, _, _ = _run(amb, capsys, "status")
    assert code != 0


# --- status (US2) ------------------------------------------------------------------


def test_status_tabela(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {"README.md": "a"})
    amb.registrar("legada_b", {}, status="curated")
    _run(amb, capsys, "inventory", "demo_a")
    code, out, _ = _run(amb, capsys, "status")
    assert code == 0
    linhas = out.splitlines()
    assert linhas[0].split() == [
        "ALIAS", "SITUAÇÃO", "PEND", "TRIA", "RASC", "REVI", "PROM", "FALH", "DESC", "REMO"
    ]  # fmt: skip
    assert linhas[1].split() == ["demo_a", "incompleta", "1", "0", "0", "0", "0", "0", "0", "0"]
    assert linhas[2].split()[:3] == ["legada_b", "sem", "inventário"]


def test_status_json_e_falhas(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {"README.md": "a"})
    _run(amb, capsys, "inventory", "demo_a")
    arquivo = amb.store_dir("demo_a") / "state.json"
    doc = json.loads(arquivo.read_text("utf-8"))
    doc["artifacts"]["README.md"].update(stage="failed", last_error="timeout")
    arquivo.write_text(json.dumps(doc), encoding="utf-8")
    code, out, _ = _run(amb, capsys, "status", "demo_a")
    assert code == 0
    assert "README.md: timeout" in out
    code, out, _ = _run(amb, capsys, "status", "demo_a", "--json")
    dados = json.loads(out)
    assert dados["folders"][0]["situation"] == "incomplete"
    assert dados["folders"][0]["counts"]["failed"] == 1
    assert dados["folders"][0]["failures"] == [{"path": "README.md", "error": "timeout"}]


def test_status_estado_invalido(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {})
    amb.store_dir("demo_a").mkdir(parents=True)
    (amb.store_dir("demo_a") / "state.json").write_text("{", encoding="utf-8")
    code, out, _ = _run(amb, capsys, "status")
    assert code == 1
    assert "estado inválido" in out
    code, out, _ = _run(amb, capsys, "status", "--json")
    assert code == 1
    assert json.loads(out)["folders"][0]["situation"] == "invalid"


def test_status_alias_inexistente(amb: _Ambiente, capsys: pytest.CaptureFixture[str]) -> None:
    amb.registrar("demo_a", {})
    assert _run(amb, capsys, "status", "nao_existe")[0] == 1
