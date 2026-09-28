# -*- coding: utf-8 -*-
"""
NOME: test_structure_similarity.py
TITULO: Testes de falha — esqueleto estrutural e pontuação de similaridade (feature 011)
DATA: 28/09/2026 16:06
MODIFICADO: 28/09/2026 16:06
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.structure_similarity
HISTÓRICO:
    - 28/09/2026 16:06: criação (T032, T033, feature 011)
STATUS: DEV
"""

import pytest

from praxisforge.domain.structure_similarity import (
    SimilarityCheck,
    skeleton_of,
    structural_score,
)

ORIGINAL_EN = """---
name: x
---
# Constraint-driven development

Intro paragraph.

## When to use

- New project
- Weak quality bar

## Steps

1. Write the contract
2. Wire the gates
3. Refuse to lower the bar

| Gate | Tool |
|------|------|
| lint | ruff |
| types | mypy |

```bash
make lint
```
"""

TRADUCAO_PT = """# Desenvolvimento guiado por restrições

Parágrafo de introdução.

## Quando usar

- Projeto novo
- Barra de qualidade fraca

## Passos

1. Escreva o contrato
2. Ligue os gates
3. Recuse rebaixar a barra

| Gate | Ferramenta |
|------|------------|
| lint | ruff |
| tipos | mypy |

```bash
make lint
```
"""

AUTORAL = """# Barra de qualidade escrita

Um contrato curto define o que precisa passar antes do merge; o agente não altera o contrato
para chegar ao verde. Quando uma verificação falha, corrige-se o código, e não a régua.
"""


def test_esqueleto_ignora_texto_e_frontmatter() -> None:
    assert skeleton_of(ORIGINAL_EN) == skeleton_of(TRADUCAO_PT)
    niveis = [secao[0] for secao in skeleton_of(ORIGINAL_EN)]
    assert niveis == [1, 2, 2]


def test_contagens_por_secao_em_faixas() -> None:
    passos = skeleton_of(ORIGINAL_EN)[2]
    # (nível, itens de lista, linhas de tabela, blocos de código, passos numerados), em faixas
    assert passos == (2, 0, 2, 1, 2)


def test_codigo_cercado_nao_conta_titulos() -> None:
    texto = "# A\n\n```\n# comentário, não é título\n- nem lista\n```\n"
    assert skeleton_of(texto) == ((1, 0, 0, 1, 0),)


def test_pontuacao() -> None:
    assert structural_score(skeleton_of(ORIGINAL_EN), skeleton_of(TRADUCAO_PT)) == 1.0
    assert structural_score(skeleton_of(ORIGINAL_EN), skeleton_of(AUTORAL)) <= 0.5
    assert structural_score((), ()) == 0.0
    assert 0.0 <= structural_score(skeleton_of(AUTORAL), ()) <= 1.0


@pytest.mark.parametrize(
    ("score", "juiz", "sinalizado"),
    [(0.69, False, False), (0.7, False, True), (0.1, True, True)],
)
def test_similarity_check(score: float, juiz: bool, sinalizado: bool) -> None:
    check = SimilarityCheck(score, 0.7, juiz, "motivo")
    assert check.flagged is sinalizado


@pytest.mark.parametrize(
    ("score", "limiar", "justificativa"),
    [(-0.1, 0.7, "x"), (1.1, 0.7, "x"), (0.5, 0.0, "x"), (0.5, 0.7, " ")],
)
def test_similarity_check_invalido(score: float, limiar: float, justificativa: str) -> None:
    with pytest.raises(ValueError):
        SimilarityCheck(score, limiar, False, justificativa)


def test_calibracao_par_sintetico() -> None:
    """FR-019: tradução com a mesma estrutura é sinalizada, mesmo variando dentro da faixa."""
    assert structural_score(skeleton_of(ORIGINAL_EN), skeleton_of(TRADUCAO_PT)) >= 0.7
    com_item_a_mais = TRADUCAO_PT.replace("3. Recuse", "3. Revise o contrato\n4. Recuse")
    assert structural_score(skeleton_of(ORIGINAL_EN), skeleton_of(com_item_a_mais)) >= 0.7
