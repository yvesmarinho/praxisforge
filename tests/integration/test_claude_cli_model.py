# -*- coding: utf-8 -*-
"""
NOME: test_claude_cli_model.py
TITULO: Testes de falha — adapter do CLI `claude`: isolamento (K4), erros e custo (feature 011)
DATA: 28/09/2026 15:53
MODIFICADO: 28/09/2026 15:53
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.claude_cli_model
HISTÓRICO:
    - 28/09/2026 15:53: criação (T011, feature 011) — executável `claude` falso no PATH
STATUS: DEV
"""

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from praxisforge.application.ports import ModelRequest, ModelRole
from praxisforge.domain.errors import (
    LanguageModelNotInstalledError,
    LanguageModelResponseInvalidError,
    LanguageModelTimeoutError,
    LanguageModelUnavailableError,
    LanguageModelUntestedVersionError,
)
from praxisforge.infrastructure.claude_cli_model import ClaudeCliModel
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator

ROOT = Path(__file__).parents[2]
JUIZ_OK = {"is_derivative": False, "justification": "estrutura própria"}

_FAKE = f"""#!{sys.executable}
import json, os, sys, time
from pathlib import Path
aqui = Path(__file__).parent
cenario = json.loads((aqui / "scenario.json").read_text())
if sys.argv[1:] == ["--version"]:
    print(cenario.get("version", "2.1.283 (Claude Code)"))
    sys.exit(0)
entrada = sys.stdin.read()
Path("PWNED").write_text("x")  # tenta sujar o cwd: precisa sumir junto com ele
(aqui / "record.json").write_text(json.dumps({{
    "argv": sys.argv[1:], "stdin": entrada, "cwd": os.getcwd(),
    "env": dict(os.environ), "pid": os.getpid(),
}}))
modo = cenario.get("mode", "ok")
if modo == "sleep":
    time.sleep(30)
if modo == "unknown_option":
    print("error: unknown option '--tools'", file=sys.stderr)
    sys.exit(1)
if modo == "exit1":
    print("falha em /home/fulano/segredo\\nlinha 2", file=sys.stderr)
    sys.exit(1)
if modo == "exit1_json":
    erro = {{"type": "result", "is_error": True, "result": "Not logged in · Please run /login"}}
    print(json.dumps(erro))
    sys.exit(1)
if modo == "not_json":
    print("Not logged in · Please run /login")
    sys.exit(0)
saida = {{"type": "result", "is_error": modo == "is_error", "result": "texto livre",
         "total_cost_usd": cenario.get("cost", 0.0051),
         "modelUsage": {{"claude-haiku-4-5-20251001": {{}}}}}}
if cenario.get("cost", 0.0051) is None:
    del saida["total_cost_usd"]
if modo != "no_structured":
    saida["structured_output"] = cenario.get("structured")
print(json.dumps(saida))
"""


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    script = bindir / "claude"
    script.write_text(_FAKE, encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("SEGREDO_X", "nao-pode-vazar")
    monkeypatch.setenv("PRAXISFORGE_ROOT", "/nao/pode/vazar")
    _cenario(bindir)
    return bindir


def _cenario(bindir: Path, **campos: Any) -> None:
    (bindir / "scenario.json").write_text(json.dumps({"structured": JUIZ_OK} | campos))


def _registro(bindir: Path) -> dict[str, Any]:
    return json.loads((bindir / "record.json").read_text())  # type: ignore[no-any-return]


def _modelo(**kwargs: Any) -> ClaudeCliModel:
    return ClaudeCliModel(
        validator=JsonSchemaContractValidator(schemas_dir=ROOT / "schemas"),
        schemas_dir=ROOT / "schemas",
        **kwargs,
    )


def _pedido(**campos: Any) -> ModelRequest:
    base: dict[str, Any] = {
        "role": ModelRole.JUDGE,
        "model": "haiku",
        "system_prompt": "Você é o juiz.",
        "user_prompt": "PROMPT-SECRETO-NO-STDIN",
        "response_schema": "curation-judge-response-v1",
        "timeout_s": 20,
        "max_budget_usd": None,
    }
    return ModelRequest(**(base | campos))


# --- isolamento (FR-005, FR-038 a FR-040) --------------------------------------------


def test_flags_de_isolamento_exatos(fake: Path) -> None:
    resposta = _modelo().complete(_pedido())
    argv = _registro(fake)["argv"]
    assert argv[0] == "-p"
    assert argv[argv.index("--model") + 1] == "haiku"
    assert argv[argv.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in argv
    assert json.loads(argv[argv.index("--mcp-config") + 1]) == {"mcpServers": {}}
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert "--disable-slash-commands" in argv
    assert "--no-session-persistence" in argv
    assert argv[argv.index("--system-prompt") + 1] == "Você é o juiz."
    assert argv[argv.index("--output-format") + 1] == "json"
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    assert schema["required"] == ["is_derivative", "justification"]
    assert "_meta" not in schema
    # o CLI recusa o metaschema draft 2020-12 (achado do teste live, 28/09/2026)
    assert "$schema" not in schema and "$id" not in schema
    for proibido in ("--bare", "--permission-mode", "--allowedTools", "--allowed-tools",
                     "--dangerously-skip-permissions", "--max-budget-usd"):  # fmt: skip
        assert proibido not in argv
    assert resposta.payload == JUIZ_OK


def test_prompt_vai_pelo_stdin(fake: Path) -> None:
    _modelo().complete(_pedido())
    registro = _registro(fake)
    assert registro["stdin"] == "PROMPT-SECRETO-NO-STDIN"
    assert all("PROMPT-SECRETO" not in arg for arg in registro["argv"])


def test_cwd_temporario_e_removido(fake: Path, tmp_path: Path) -> None:
    _modelo().complete(_pedido())
    cwd = Path(_registro(fake)["cwd"])
    assert cwd != Path.cwd() and not str(cwd).startswith(str(ROOT))
    assert not cwd.exists()


def test_env_so_com_lista_de_permissao(fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LC_ALL", "pt_BR.UTF-8")
    _modelo().complete(_pedido())
    env = _registro(fake)["env"]
    assert "SEGREDO_X" not in env and "PRAXISFORGE_ROOT" not in env
    assert env["LC_ALL"] == "pt_BR.UTF-8"
    assert set(env) <= {"HOME", "PATH", "LANG", "TERM", "TMPDIR", "CLAUDE_CONFIG_DIR"} | {
        k for k in env if k.startswith("LC_")
    }


def test_max_budget_so_quando_informado(fake: Path) -> None:
    _modelo().complete(_pedido(max_budget_usd=Decimal("0.25")))
    argv = _registro(fake)["argv"]
    assert argv[argv.index("--max-budget-usd") + 1] == "0.25"


# --- falha fechada (FR-037) ------------------------------------------------------------


def test_versao_fora_da_faixa(fake: Path) -> None:
    _cenario(fake, version="2.2.0 (Claude Code)")
    with pytest.raises(LanguageModelUntestedVersionError, match="2.2.0"):
        _modelo().check_ready()
    assert not (fake / "record.json").exists()
    _modelo(allow_untested=True).check_ready()


@pytest.mark.parametrize("versao", ["2.1.282 (Claude Code)", "sem versão", "1.9.999"])
def test_versoes_recusadas(fake: Path, versao: str) -> None:
    _cenario(fake, version=versao)
    with pytest.raises(LanguageModelUntestedVersionError):
        _modelo().check_ready()


def test_flag_recusado_falha_fechada(fake: Path) -> None:
    _cenario(fake, mode="unknown_option")
    with pytest.raises(LanguageModelUntestedVersionError, match="flag"):
        _modelo().complete(_pedido())


def test_executavel_ausente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(LanguageModelNotInstalledError):
        _modelo().check_ready()
    with pytest.raises(LanguageModelNotInstalledError):
        _modelo().complete(_pedido())


# --- erros de chamada ------------------------------------------------------------------


def test_timeout_encerra_o_processo(fake: Path) -> None:
    _cenario(fake, mode="sleep")
    with pytest.raises(LanguageModelTimeoutError):
        _modelo().complete(_pedido(timeout_s=1))
    registro = _registro(fake)
    with pytest.raises(ProcessLookupError):
        os.kill(registro["pid"], 0)
    assert not Path(registro["cwd"]).exists()


@pytest.mark.parametrize("modo", ["is_error", "not_json", "exit1"])
def test_indisponivel(fake: Path, modo: str) -> None:
    _cenario(fake, mode=modo)
    with pytest.raises(LanguageModelUnavailableError) as erro:
        _modelo().complete(_pedido())
    mensagem = str(erro.value)
    assert "/home/fulano" not in mensagem and "linha 2" not in mensagem
    assert len(mensagem) < 400


def test_mensagem_do_stderr_limitada(fake: Path) -> None:
    _cenario(fake, mode="exit1")
    with pytest.raises(LanguageModelUnavailableError, match=r"/home/\*\*\*"):
        _modelo().complete(_pedido())


@pytest.mark.parametrize(
    "cenario",
    [{"mode": "no_structured"}, {"structured": {"is_derivative": "talvez", "justification": "x"}},
     {"structured": None}],
)  # fmt: skip
def test_resposta_invalida(fake: Path, cenario: dict[str, Any]) -> None:
    _cenario(fake, **cenario)
    with pytest.raises(LanguageModelResponseInvalidError):
        _modelo().complete(_pedido())


# --- custo e modelo real ------------------------------------------------------------


def test_custo_e_modelo(fake: Path) -> None:
    resposta = _modelo().complete(_pedido())
    assert resposta.cost_usd == Decimal("0.0051")
    assert resposta.model == "claude-haiku-4-5-20251001"


def test_custo_ausente(fake: Path) -> None:
    _cenario(fake, cost=None)
    assert _modelo().complete(_pedido()).cost_usd is None


def test_exit_com_json_no_stdout_mostra_o_motivo(fake: Path) -> None:
    _cenario(fake, mode="exit1_json")
    with pytest.raises(LanguageModelUnavailableError, match="Not logged in"):
        _modelo().complete(_pedido())


def test_schema_enviado_sem_combinacao_na_raiz_mas_validado_por_inteiro(fake: Path) -> None:
    """A API recusa allOf/anyOf/oneOf na raiz do input_schema (achado da triagem real)."""
    triagem: dict[str, Any] = {
        "verdict": "covered", "justification": "x", "covered_by": [], "merge_target": None,
        "suggested_kind": None, "ideas_summary": None,
    }  # fmt: skip
    _cenario(fake, structured=triagem)
    with pytest.raises(LanguageModelResponseInvalidError):  # a regra do allOf vale localmente
        _modelo().complete(_pedido(response_schema="curation-triage-response-v1"))
    argv = _registro(fake)["argv"]
    enviado = json.loads(argv[argv.index("--json-schema") + 1])
    assert not {"allOf", "anyOf", "oneOf"} & set(enviado)
    assert enviado["required"][0] == "verdict"
