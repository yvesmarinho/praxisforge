# -*- coding: utf-8 -*-
"""
NOME: prompt_set.py
TITULO: Conjunto de prompts de curadoria versionados e sua impressão digital (feature 011)
DATA: 28/09/2026 15:54
MODIFICADO: 28/09/2026 15:54
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 28/09/2026 15:54: criação (T014, feature 011) — faz test_prompt_set.py passar
STATUS: DEV
"""

import hashlib
from dataclasses import dataclass, field

from praxisforge.domain.errors import PromptSetError

PROMPT_FILES = ("criteria.md", "draft.md", "judge.md", "triage.md")


@dataclass(frozen=True)
class PromptSet:
    """
    Prompts de triagem, rascunho e juiz, e os critérios (C6, FR-020, FR-021).

    :raises PromptSetError: algum prompt vazio.

    :Example:

    >>> len(PromptSet("t", "d", "j", "c").fingerprint)
    64
    """

    triage: str
    draft: str
    judge: str
    criteria: str
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        textos = self.by_file()
        for nome, texto in textos.items():
            if not texto.strip():
                raise PromptSetError(nome, "está vazio")
        resumo = hashlib.sha256()
        for nome in PROMPT_FILES:
            resumo.update(nome.encode("utf-8") + b"\0" + textos[nome].encode("utf-8") + b"\0")
        object.__setattr__(self, "fingerprint", resumo.hexdigest())

    def by_file(self) -> dict[str, str]:
        """Conteúdo por nome de arquivo, na ordem canônica."""
        return {
            "criteria.md": self.criteria,
            "draft.md": self.draft,
            "judge.md": self.judge,
            "triage.md": self.triage,
        }
