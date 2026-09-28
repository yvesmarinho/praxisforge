# -*- coding: utf-8 -*-
"""
NOME: test_cli_curation_triage.py
TITULO: Testes de falha — CLI praxisforge curation triage e colunas novas do status (feature 011)
DATA: 28/09/2026 16:00
MODIFICADO: 28/09/2026 16:00
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli, tests.triage_helpers
HISTÓRICO:
    - 28/09/2026 16:00: criação — US1 (T025, feature 011)
STATUS: DEV
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from praxisforge.application.ports import ModelRole
from praxisforge.domain.errors import (
    LanguageModelNotInstalledError,
    LanguageModelResponseInvalidError,
    LanguageModelUnavailableError,
    LanguageModelUntestedVersionError,
)
from praxisforge.presentation import cli
from tests.triage_helpers import TriageEnv, triagem

TRES = {"a.md": "# A", "b.md": "# B", "c.md": "# C"}


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TriageEnv:
    ambiente = TriageEnv(tmp_path)
    monkeypatch.setenv("PRAXISFORGE_ROOT", str(ambiente.project))
    monkeypatch.setattr(cli, "_criar_modelo", lambda *_a, **_k: ambiente.model)
    return ambiente


def _run(env: TriageEnv, capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    codigo = cli.main(["--registry", str(env.registry), "curation", *argv])
    capturado = capsys.readouterr()
    return codigo, capturado.out, capturado.err


def test_triagem_ok(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    capsys.readouterr()
    codigo, out, err = _run(env, capsys, "triage", "demo_a")
    assert codigo == 0, err
    assert "demo_a: 3 triados (0 cobertos, 0 lacunas, 3 fora de escopo)" in out
    assert "0 restantes" in out
    assert "Resumo: 3 chamadas, US$ 0,03, parada: concluída" in out
    assert str(env.base) not in out + err


def test_uso(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    assert _run(env, capsys, "triage")[0] == 2
    assert _run(env, capsys, "triage", "demo_a", "--all")[0] == 2


@pytest.mark.parametrize(
    "opcao",
    [["--max-calls", "0"], ["--max-cost-usd", "0"], ["--timeout", "5"],
     ["--similarity-threshold", "0"], ["--similarity-threshold", "1.5"],
     ["--max-consecutive-failures", "0"]],
)  # fmt: skip
def test_opcoes_fora_do_intervalo(
    env: TriageEnv, capsys: pytest.CaptureFixture[str], opcao: list[str]
) -> None:
    env.registrar("demo_a", TRES)
    assert _run(env, capsys, "triage", "demo_a", *opcao)[0] == 2
    assert env.model.calls() == 0


def test_alias_inexistente_e_nao_inventariado(
    env: TriageEnv, capsys: pytest.CaptureFixture[str]
) -> None:
    env.registrar("demo_a", TRES, inventariar=False)
    assert _run(env, capsys, "triage", "nao_existe")[0] == 1
    codigo, _, err = _run(env, capsys, "triage", "demo_a")
    assert codigo == 1 and "curation inventory demo_a" in err


@pytest.mark.parametrize(
    "erro", [LanguageModelNotInstalledError("claude"), LanguageModelUntestedVersionError("2.9.0")]
)
def test_ambiente_do_modelo(
    env: TriageEnv, capsys: pytest.CaptureFixture[str], erro: Exception
) -> None:
    env.registrar("demo_a", TRES)
    env.model.ready_error = erro
    codigo, _, err = _run(env, capsys, "triage", "demo_a")
    assert codigo == 3 and "claude" in err or "2.9.0" in err
    assert env.model.calls() == 0


def test_lock_ocupado_exit_3(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    """Achado C2 da análise: duas triagens na mesma pasta ao mesmo tempo."""
    env.registrar("demo_a", TRES)
    with env.store.lock("demo_a"):
        assert _run(env, capsys, "triage", "demo_a")[0] == 3
    assert env.model.calls() == 0


def test_falha_de_artefato_exit_1_no_stderr(
    env: TriageEnv, capsys: pytest.CaptureFixture[str]
) -> None:
    env.registrar("demo_a", TRES)
    env.model.script(ModelRole.TRIAGE, "b.md", LanguageModelResponseInvalidError("x"))
    codigo, out, err = _run(env, capsys, "triage", "demo_a")
    assert codigo == 1
    assert "demo_a:b.md: LanguageModelResponseInvalidError" in err
    assert "1 falha" in out


def test_status_com_vereditos(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    env.model.script(ModelRole.TRIAGE, "a.md", triagem("gap", suggested_kind="rule"))
    env.model.default(ModelRole.DRAFT, LanguageModelResponseInvalidError("sem rascunho"))
    _run(env, capsys, "triage", "demo_a")
    codigo, out, _ = _run(env, capsys, "status", "demo_a")
    cabecalho, linha = out.splitlines()[:2]
    assert cabecalho.split()[-4:] == ["COB", "LAC", "FORA", "ALERTA"]
    assert linha.split()[-4:] == ["0", "1", "2", "0"]
    _, out_json, _ = _run(env, capsys, "status", "demo_a", "--json")
    pasta: dict[str, Any] = json.loads(out_json)["folders"][0]
    assert pasta["verdicts"] == {"covered": 0, "gap": 1, "out_of_scope": 2}
    assert pasta["similarity_alerts"] == 0


# --- US2: rascunhos na saída e alertas no status -----------------------------------------

ORIGINAL = "# A\n\n## B\n\n- x\n- y\n\n## C\n\n1. a\n2. b\n3. c\n"
COPIA = {"kind": "rule", "name": "copia-estrutural", "description": "Cópia.", "body": ORIGINAL}


def test_rascunho_com_alerta_na_saida_e_no_status(
    env: TriageEnv, capsys: pytest.CaptureFixture[str]
) -> None:
    env.registrar("demo_a", {"rules/a.md": ORIGINAL})
    env.model.default(ModelRole.TRIAGE, triagem("gap"))
    env.model.default(ModelRole.DRAFT, COPIA)
    codigo, out, err = _run(env, capsys, "triage", "demo_a")
    assert codigo == 0, err
    assert "1 rascunhos (1 com alerta)" in out
    _, status, _ = _run(env, capsys, "status", "demo_a")
    assert status.splitlines()[1].split()[-4:] == ["0", "1", "0", "1"]


def test_rascunho_corrompido_exit_1(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", {"rules/a.md": "a"})
    area = env.registry.parent / "curation" / "_drafts"
    area.mkdir(parents=True)
    (area / "0123456789abcdef.json").write_text("{", encoding="utf-8")
    codigo, _, err = _run(env, capsys, "triage", "demo_a")
    assert codigo == 1 and "0123456789abcdef" in err
    assert _run(env, capsys, "status", "demo_a")[0] == 1


# --- US3: teto, interrupção e custo ---------------------------------------------------------


def test_teto_exit_4_com_retomada(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    codigo, out, _ = _run(env, capsys, "triage", "demo_a", "--max-calls", "2")
    assert codigo == 4
    assert "parada: teto atingido" in out
    assert "Para continuar: praxisforge curation triage demo_a" in out
    codigo, out, _ = _run(env, capsys, "triage", "--all", "--max-calls", "1")
    assert codigo == 0 and env.model.calls() == 3  # o 3º artefato coube na retomada


def test_interrompido_exit_130(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    env.model.script(ModelRole.TRIAGE, "b.md", KeyboardInterrupt())
    codigo, _, err = _run(env, capsys, "triage", "demo_a")
    assert codigo == 130 and "interrompido" in err


def test_custo_nao_mensuravel(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    env.model.cost = None
    codigo, out, _ = _run(env, capsys, "triage", "demo_a", "--max-cost-usd", "0.01")
    assert codigo == 0
    assert "custo não informado" in out
    assert "custo: não mensurável (teto em US$ ignorado)" in out


def test_custo_em_formato_pt_br(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", {f"{n:04d}.md": "x" for n in range(3)})
    env.model.cost = Decimal("1234.5")
    _, out, _ = _run(env, capsys, "triage", "demo_a")
    assert "US$ 3.703,50" in out


def test_falhas_consecutivas_exit_3(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    env.model.default(ModelRole.TRIAGE, LanguageModelUnavailableError("fora do ar"))
    codigo, out, _ = _run(env, capsys, "triage", "demo_a", "--max-consecutive-failures", "2")
    assert codigo == 3 and "falhas consecutivas do modelo" in out


def test_max_cost_nao_numerico(env: TriageEnv, capsys: pytest.CaptureFixture[str]) -> None:
    env.registrar("demo_a", TRES)
    assert _run(env, capsys, "triage", "demo_a", "--max-cost-usd", "abc")[0] == 2
