# -*- coding: utf-8 -*-
"""
NOME: structure_similarity.py
TITULO: Esqueleto estrutural de Markdown e similaridade independente de idioma (feature 011)
DATA: 28/09/2026 16:07
MODIFICADO: 28/09/2026 16:07
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 28/09/2026 16:07: criação (T037, feature 011) — faz test_structure_similarity.py passar
STATUS: DEV
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher

Section = tuple[int, int, int, int, int]
Skeleton = tuple[Section, ...]

_TITULO = re.compile(r"^(#{1,6})\s+\S")
_LISTA = re.compile(r"^\s*[-*+]\s+\S")
_PASSO = re.compile(r"^\s*\d+[.)]\s+\S")
_TABELA = re.compile(r"^\s*\|")
_SEPARADOR = re.compile(r"^\s*\|?\s*:?-{3,}")
_CERCA = re.compile(r"^\s*(```|~~~)")
_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _faixa(n: int) -> int:
    """0 → 0; 1–2 → 1; 3–5 → 2; 6+ → 3 (variação dentro da faixa não muda o esqueleto)."""
    if n == 0:
        return 0
    if n <= 2:
        return 1
    return 2 if n <= 5 else 3


def skeleton_of(markdown: str) -> Skeleton:
    """
    Sequência de seções `(nível, itens de lista, linhas de tabela, blocos de código, passos)`,
    com contagens em faixas. Não depende do texto: pega cópia e tradução (R7).

    :param markdown: documento (o frontmatter é ignorado).
    :return: esqueleto.
    :rtype: Skeleton

    :Example:

    >>> skeleton_of("# A\\n\\n- x\\n- y\\n")
    ((1, 1, 0, 0, 0),)
    """
    texto = _FRONTMATTER.sub("", markdown, count=1)
    secoes: list[list[int]] = []
    atual: list[int] | None = None
    em_codigo = False
    for linha in texto.splitlines():
        if _CERCA.match(linha):
            if not em_codigo:
                atual = atual if atual is not None else _nova(secoes, 0)
                atual[3] += 1
            em_codigo = not em_codigo
            continue
        if em_codigo:
            continue
        titulo = _TITULO.match(linha)
        if titulo:
            atual = _nova(secoes, len(titulo.group(1)))
            continue
        if not linha.strip():
            continue
        atual = atual if atual is not None else _nova(secoes, 0)
        if _LISTA.match(linha):
            atual[1] += 1
        elif _PASSO.match(linha):
            atual[4] += 1
        elif _TABELA.match(linha) and not _SEPARADOR.match(linha):
            atual[2] += 1
    return tuple((s[0], _faixa(s[1]), _faixa(s[2]), _faixa(s[3]), _faixa(s[4])) for s in secoes)


def _nova(secoes: list[list[int]], nivel: int) -> list[int]:
    secao = [nivel, 0, 0, 0, 0]
    secoes.append(secao)
    return secao


def structural_score(a: Sequence[Section], b: Sequence[Section]) -> float:
    """
    Sobreposição de estrutura em [0, 1] (`SequenceMatcher.ratio`); vazio × vazio = 0.

    :Example:

    >>> structural_score(((1, 0, 0, 0, 0),), ((1, 0, 0, 0, 0),))
    1.0
    """
    if not a and not b:
        return 0.0
    return SequenceMatcher(None, list(a), list(b), autojunk=False).ratio()


@dataclass(frozen=True)
class SimilarityCheck:
    """
    Resultado das duas camadas de verificação de um rascunho (FR-017).

    :raises ValueError: pontuação fora de [0, 1], limiar fora de (0, 1] ou justificativa vazia.
    """

    structural_score: float
    threshold: float
    judge_is_derivative: bool
    judge_justification: str
    flagged: bool = field(init=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.structural_score <= 1.0:
            raise ValueError("pontuação estrutural fora de [0, 1]")
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError("limiar fora de (0, 1]")
        if not self.judge_justification.strip():
            raise ValueError("justificativa do juiz vazia")
        sinalizado = self.structural_score >= self.threshold or self.judge_is_derivative
        object.__setattr__(self, "flagged", sinalizado)
