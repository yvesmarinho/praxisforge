# -*- coding: utf-8 -*-
"""
NOME: filesystem_prompt_source.py
TITULO: Adapter PromptSource — lê os prompts versionados de prompts/curation/ (feature 011)
DATA: 28/09/2026 15:55
MODIFICADO: 28/09/2026 15:55
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports
HISTÓRICO:
    - 28/09/2026 15:55: criação (T018, feature 011) — faz test_filesystem_prompt_source.py passar
STATUS: DEV
"""

from pathlib import Path

from praxisforge.application.ports import PromptSource
from praxisforge.domain.errors import PromptSetError
from praxisforge.domain.prompt_set import PROMPT_FILES, PromptSet


class FilesystemPromptSource(PromptSource):
    """
    Lê `triage.md`, `draft.md`, `judge.md` e `criteria.md` do diretório informado.

    :param prompts_dir: `<raiz do projeto>/prompts/curation`.
    :type prompts_dir: Path
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir

    def load(self) -> PromptSet:
        """Ver PromptSource.load (mensagens sem caminho absoluto)."""
        textos: dict[str, str] = {}
        for nome in PROMPT_FILES:
            try:
                textos[nome] = (self._dir / nome).read_text(encoding="utf-8")
            except FileNotFoundError as error:
                raise PromptSetError(nome, "não encontrado em prompts/curation/") from error
            except (OSError, UnicodeDecodeError) as error:
                raise PromptSetError(nome, f"ilegível ({type(error).__name__})") from error
        return PromptSet(
            triage=textos["triage.md"],
            draft=textos["draft.md"],
            judge=textos["judge.md"],
            criteria=textos["criteria.md"],
        )
