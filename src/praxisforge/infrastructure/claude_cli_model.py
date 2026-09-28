# -*- coding: utf-8 -*-
"""
NOME: claude_cli_model.py
TITULO: Adapter LanguageModel — CLI `claude` sem ferramentas, isolado e com falha fechada
DATA: 28/09/2026 15:56
MODIFICADO: 28/09/2026 15:56
VERSÃO: 0.1.0
DEPEND: subprocess, praxisforge.application.ports (CLI `claude` 2.1.x no PATH)
HISTÓRICO:
    - 28/09/2026 15:56: criação (T019, feature 011) — faz test_claude_cli_model.py passar
STATUS: DEV
"""

import json
import logging
import os
import re
import shutil
import signal
import subprocess  # nosec B404 - só argv fixo, sem shell (K4, research R1)
import tempfile
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from praxisforge.application.ports import (
    ContractValidator,
    LanguageModel,
    ModelReply,
    ModelRequest,
)
from praxisforge.domain.errors import (
    LanguageModelNotInstalledError,
    LanguageModelResponseInvalidError,
    LanguageModelTimeoutError,
    LanguageModelUnavailableError,
    LanguageModelUntestedVersionError,
    PraxisForgeError,
)

logger = logging.getLogger(__name__)

# Faixa em que o isolamento foi comprovado com o teste live (FR-037, research R1).
TESTED_MIN = (2, 1, 283)
TESTED_MAX_EXCLUSIVE = (2, 2, 0)
_ENV_PERMITIDO = frozenset({"HOME", "PATH", "LANG", "TERM", "TMPDIR", "CLAUDE_CONFIG_DIR"})
_VERSAO = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_HOME = re.compile(r"/(home|Users)/[^/\s]+")  # diretório pessoal (Linux/macOS)
_FLAG_RECUSADO = re.compile(r"unknown option|unrecognized|unknown argument", re.IGNORECASE)
_LIMITE_MENSAGEM = 200


def _env_isolado(origem: Mapping[str, str]) -> dict[str, str]:
    """Só as variáveis da lista de permissão e `LC_*` (FR-039)."""
    return {k: v for k, v in origem.items() if k in _ENV_PERMITIDO or k.startswith("LC_")}


def _resumo_erro(texto: str) -> str:
    """1ª linha, até 200 caracteres, com o diretório pessoal mascarado (FR-034)."""
    linhas = texto.strip().splitlines()
    primeira = linhas[0] if linhas else "sem mensagem"
    return _HOME.sub(r"/\1/***", primeira)[:_LIMITE_MENSAGEM]


class ClaudeCliModel(LanguageModel):
    """
    Chama `claude -p` sem nenhuma ferramenta, MCP, setting, skill ou sessão (K4, FR-038).

    O prompt vai pelo stdin (FR-040); o processo roda num diretório temporário vazio, removido
    ao fim, com ambiente filtrado (FR-039). A resposta é o `structured_output`, validado de novo
    aqui contra o schema (FR-007).

    :param validator: validador de contratos (a validação que vale é a do código).
    :type validator: ContractValidator
    :param schemas_dir: diretório `schemas/` (o schema vai também para `--json-schema`).
    :type schemas_dir: Path
    :param executable: nome do executável no PATH.
    :type executable: str
    :param allow_untested: aceita versão fora da faixa testada (`--allow-untested-cli`).
    :type allow_untested: bool
    """

    def __init__(
        self,
        validator: ContractValidator,
        schemas_dir: Path,
        executable: str = "claude",
        allow_untested: bool = False,
    ) -> None:
        self._validator = validator
        self._schemas_dir = schemas_dir
        self._executable = executable
        self._allow_untested = allow_untested

    def _resolve(self) -> str:
        caminho = shutil.which(self._executable, path=os.environ.get("PATH"))
        if caminho is None:
            raise LanguageModelNotInstalledError(self._executable)
        return caminho

    def check_ready(self) -> None:
        """Ver LanguageModel.check_ready (`claude --version` na faixa testada)."""
        executavel = self._resolve()
        try:
            saida = subprocess.run(  # noqa: S603 # nosec B603 - argv fixo, sem shell
                [executavel, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                env=_env_isolado(os.environ),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise LanguageModelNotInstalledError(self._executable) from error
        encontrada = _VERSAO.search(saida.stdout)
        if encontrada is None:
            raise LanguageModelUntestedVersionError("versão do CLI não reconhecida")
        versao = tuple(int(parte) for parte in encontrada.groups())
        if self._allow_untested:
            logger.warning("CLI fora da faixa testada aceito por --allow-untested-cli")
            return
        if not TESTED_MIN <= versao < TESTED_MAX_EXCLUSIVE:
            raise LanguageModelUntestedVersionError(
                f"versão {encontrada.group(0)} fora da faixa testada "
                f"{'.'.join(map(str, TESTED_MIN))} até <{'.'.join(map(str, TESTED_MAX_EXCLUSIVE))}"
            )

    def _schema(self, nome: str) -> str:
        documento = json.loads((self._schemas_dir / f"{nome}.json").read_text(encoding="utf-8"))
        # O CLI valida o schema com um metaschema próprio e recusa "$schema" draft 2020-12
        # (achado do teste live); a validação que vale continua sendo a local, com o schema
        # completo.
        # A API também recusa allOf/anyOf/oneOf na raiz do input_schema (achado da triagem
        # real): as regras condicionais ficam só na validação local e no domínio.
        for chave in ("_meta", "$schema", "$id", "allOf", "anyOf", "oneOf"):
            documento.pop(chave, None)
        return json.dumps(documento, ensure_ascii=False)

    def _argv(self, executavel: str, request: ModelRequest) -> list[str]:
        argv = [
            executavel,
            "-p",
            "--model", request.model,
            "--tools", "",
            "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}',
            "--setting-sources", "",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--system-prompt", request.system_prompt,
            "--output-format", "json",
            "--json-schema", self._schema(request.response_schema),
        ]  # fmt: skip
        if request.max_budget_usd is not None:
            argv += ["--max-budget-usd", str(request.max_budget_usd)]
        return argv

    def complete(self, request: ModelRequest) -> ModelReply:
        """Ver LanguageModel.complete."""
        argv = self._argv(self._resolve(), request)
        with tempfile.TemporaryDirectory(prefix="praxisforge-llm-") as cwd:
            try:
                processo = subprocess.Popen(  # noqa: S603 # nosec B603 - argv fixo, sem shell
                    argv,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=cwd,
                    env=_env_isolado(os.environ),
                    start_new_session=True,
                )
            except OSError as error:
                raise LanguageModelNotInstalledError(self._executable) from error
            try:
                stdout, stderr = processo.communicate(
                    request.user_prompt, timeout=request.timeout_s
                )
            except subprocess.TimeoutExpired as error:
                self._encerrar(processo)
                raise LanguageModelTimeoutError(request.timeout_s) from error
            except BaseException:
                self._encerrar(processo)
                raise
        return self._interpretar(request, processo.returncode, stdout, stderr)

    @staticmethod
    def _encerrar(processo: "subprocess.Popen[str]") -> None:
        try:
            os.killpg(processo.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        processo.communicate()

    def _interpretar(
        self, request: ModelRequest, codigo: int, stdout: str, stderr: str
    ) -> ModelReply:
        if codigo != 0:
            if _FLAG_RECUSADO.search(stderr):
                raise LanguageModelUntestedVersionError(
                    f"flag de isolamento recusado pelo CLI: {_resumo_erro(stderr)}"
                )
            motivo = stderr.strip() or self._resultado(stdout)
            raise LanguageModelUnavailableError(f"exit {codigo}: {_resumo_erro(motivo)}")
        try:
            documento: Any = json.loads(stdout)
        except json.JSONDecodeError as error:
            raise LanguageModelUnavailableError(
                f"saída não é JSON: {_resumo_erro(stdout)}"
            ) from error
        if not isinstance(documento, dict):
            raise LanguageModelUnavailableError("saída JSON não é um objeto")
        if documento.get("is_error"):
            raise LanguageModelUnavailableError(_resumo_erro(str(documento.get("result", ""))))
        payload = documento.get("structured_output")
        if not isinstance(payload, dict):
            raise LanguageModelResponseInvalidError("sem saída estruturada")
        try:
            self._validator.validate(payload, request.response_schema)
        except PraxisForgeError as error:
            raise LanguageModelResponseInvalidError(str(error)[:_LIMITE_MENSAGEM]) from error
        return ModelReply(
            payload=payload, cost_usd=self._custo(documento), model=self._modelo(documento, request)
        )

    @staticmethod
    def _resultado(stdout: str) -> str:
        """Campo `result` do JSON do CLI (onde ele põe o motivo de erros como "Not logged in")."""
        try:
            documento = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout
        return str(documento.get("result", "")) if isinstance(documento, dict) else stdout

    @staticmethod
    def _custo(documento: Mapping[str, Any]) -> Decimal | None:
        bruto = documento.get("total_cost_usd")
        if bruto is None or isinstance(bruto, bool):
            return None
        try:
            custo = Decimal(str(bruto))
        except InvalidOperation:
            return None
        return custo if custo >= 0 else None

    @staticmethod
    def _modelo(documento: Mapping[str, Any], request: ModelRequest) -> str:
        uso = documento.get("modelUsage")
        if isinstance(uso, dict) and uso:
            return str(sorted(uso)[0])
        return request.model
