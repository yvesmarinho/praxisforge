# -*- coding: utf-8 -*-
"""
NOME: git_cli_inspector.py
TITULO: Adapter GitContentInspector — consulta o executável git (sem dependência nova)
DATA: 23/09/2026 12:05
MODIFICADO: 23/09/2026 12:06
VERSÃO: 0.1.0
DEPEND: git (executável ≥ 2.x), praxisforge.application.ports, praxisforge.domain.errors
HISTÓRICO:
    - 23/09/2026 12:05: criação (T016, feature 004-deteccao-mudanca-conteudo) — faz
      tests/integration/test_git_cli_inspector.py passar
STATUS: DEV
"""

import logging
import os
import re
import subprocess  # nosec B404 - chamadas com argumentos fixos, sem shell (research §R1)
from pathlib import Path

from praxisforge.application.ports import GitContentInspector
from praxisforge.domain.errors import ContentInspectionError

logger = logging.getLogger(__name__)

_COMMIT_HASH_PATTERN = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_NOT_A_REPOSITORY = "not a git repository"


class GitCliInspector(GitContentInspector):
    """
    Adapter que responde fatos sobre o conteúdo versionado de uma pasta via `git -C <pasta>`.

    Toda chamada usa lista de argumentos (`shell=False`), timeout e locale `C` para que a
    saída seja previsível. Nenhuma mensagem de erro inclui caminho absoluto.

    :param timeout: limite em segundos por chamada ao git (FR-009).
    :type timeout: float
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def head_commit(self, path: Path) -> str | None:
        """Ver GitContentInspector.head_commit."""
        if not self._inside_work_tree(path):
            return None
        result = self._run(path, "rev-parse", "--verify", "-q", "HEAD")
        if result.returncode != 0:
            return None
        head = result.stdout.strip()
        if not _COMMIT_HASH_PATTERN.match(head):
            raise ContentInspectionError("", "saída inesperada do git ao ler o HEAD")
        return head

    def changed_since(self, path: Path, commit: str) -> bool:
        """Ver GitContentInspector.changed_since."""
        if not _COMMIT_HASH_PATTERN.match(commit):
            raise ContentInspectionError("", "hash gravado fora do formato")
        if not self._inside_work_tree(path):
            raise ContentInspectionError("", "pasta não está num repositório git")
        existe = self._run(path, "cat-file", "-e", f"{commit}^{{commit}}")
        if existe.returncode != 0:
            logger.info("commit gravado ausente do histórico; tratado como mudança")
            return True
        diff = self._run(path, "diff", "--quiet", "--no-ext-diff", commit, "HEAD", "--", ".")
        if diff.returncode == 0:
            return False
        if diff.returncode == 1:
            return True
        raise ContentInspectionError("", f"git diff terminou com código {diff.returncode}")

    def _inside_work_tree(self, path: Path) -> bool:
        result = self._run(path, "rev-parse", "--is-inside-work-tree")
        if result.returncode == 0:
            return result.stdout.strip() == "true"
        if _NOT_A_REPOSITORY in result.stderr:
            return False
        raise ContentInspectionError("", f"git rev-parse terminou com código {result.returncode}")

    def _run(self, path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}
        try:
            return subprocess.run(  # noqa: S603 # nosec B603 - argumentos fixos, hash validado
                ["git", "-C", str(path), *args],  # noqa: S607 - git resolvido pelo PATH
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
                env=env,
            )
        except FileNotFoundError as error:
            logger.error("executável git indisponível", exc_info=True)
            raise ContentInspectionError("", "executável git indisponível") from error
        except subprocess.TimeoutExpired as error:
            logger.error("git excedeu %s s", self._timeout, exc_info=True)
            raise ContentInspectionError("", f"tempo esgotado ({self._timeout:g} s)") from error
        except OSError as error:
            logger.error("falha ao executar git", exc_info=True)
            raise ContentInspectionError("", "falha ao executar git") from error
