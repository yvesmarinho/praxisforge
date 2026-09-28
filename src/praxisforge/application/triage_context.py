# -*- coding: utf-8 -*-
"""
NOME: triage_context.py
TITULO: Contexto da triagem — itens parecidos, limites e prompt com dado não confiável delimitado
DATA: 28/09/2026 16:02
MODIFICADO: 28/09/2026 16:18
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports, praxisforge.domain
HISTÓRICO:
    - 28/09/2026 16:02: criação (T029, feature 011) — faz test_triage_context.py passar
    - 28/09/2026 16:18: índice de rascunhos, prompts de rascunho e de juiz (T040, US2)
STATUS: DEV
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from praxisforge.application.ports import CatalogItem
from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.curation_draft import Draft

SIMILAR_LIMIT = 96 * 1024
INDEX_LIMIT = 64 * 1024
MAX_SIMILAR = 3
_CABECA = 20  # linhas do artefato usadas para achar itens parecidos
_PALAVRA = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "the and for with that this from into your you are not use when how what "
    "para com que uma uns umas por dos das nas nos pelo pela como quando mais "
    "sem sobre entre este esta isso esse essa seu sua ser ter".split()
)


def tokens(texto: str) -> frozenset[str]:
    """
    Palavras normalizadas (minúsculas, sem acento, sem stopwords, ≥ 3 letras) — R6.

    :Example:

    >>> sorted(tokens("Revisão de Código"))
    ['codigo', 'revisao']
    """
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return frozenset(
        p for p in _PALAVRA.findall(sem_acento.lower()) if len(p) >= 3 and p not in _STOPWORDS
    )


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    uniao = a | b
    return len(a & b) / len(uniao) if uniao else 0.0


def select_similar(
    artifact_path: str, artifact_text: str, items: list[CatalogItem]
) -> list[CatalogItem]:
    """
    Até 3 itens do acervo mais parecidos com o artefato, sem modelo (R6, FR-011).

    Ordem: Jaccard decrescente, depois nome. Jaccard 0 fica de fora. Itens entram inteiros
    enquanto couberem em 96 KiB; o que não cabe é pulado (FR-011b).

    :param artifact_path: caminho relativo do artefato.
    :param artifact_text: conteúdo do artefato.
    :param items: itens do acervo do mesmo tipo.
    :return: itens escolhidos, em ordem.
    :rtype: list[CatalogItem]
    """
    cabeca = "\n".join(artifact_text.splitlines()[:_CABECA])
    alvo = tokens(f"{artifact_path} {cabeca}")
    pontuados = [
        (_jaccard(alvo, tokens(f"{item.name} {item.description}")), item) for item in items
    ]
    ordenados = sorted(
        ((p, i) for p, i in pontuados if p > 0), key=lambda par: (-par[0], par[1].name)
    )
    escolhidos: list[CatalogItem] = []
    usado = 0
    for _, item in ordenados:
        tamanho = len(item.content.encode("utf-8"))
        if usado + tamanho > SIMILAR_LIMIT:
            continue
        escolhidos.append(item)
        usado += tamanho
        if len(escolhidos) == MAX_SIMILAR:
            break
    return escolhidos


def truncate_index(texto: str, limite: int) -> tuple[str, bool]:
    """
    Corta um índice no último fim de linha que cabe no limite (determinístico — FR-011b).

    :return: (texto, truncou).
    :rtype: tuple[str, bool]
    """
    dados = texto.encode("utf-8")
    if len(dados) <= limite:
        return texto, False
    corte = dados[:limite]
    fim = corte.rfind(b"\n")
    return corte[: fim + 1].decode("utf-8", errors="ignore"), True


@dataclass(frozen=True)
class TriageInput:
    """Tudo o que entra no prompt de triagem de um artefato (sem caminho absoluto — FR-041)."""

    alias: str
    path: str
    kind: ArtifactKind
    restricted_license: bool
    content: str
    library_index: str
    drafts_index: str
    similar: list[CatalogItem]
    criteria: str


def _nonce(nonce: Callable[[], str], *nao_confiaveis: str) -> str:
    """Sorteia um nonce que não aparece em nenhum bloco não confiável (R5)."""
    while True:
        valor = nonce()
        if not any(valor in texto for texto in nao_confiaveis):
            return valor


def untrusted_block(marcador: str, valor: str, texto: str) -> str:
    """Bloco delimitado de dado de terceiros (FR-008, FR-042)."""
    return f"<<<{marcador} {valor}>>>\n{texto}\n<<<FIM {valor}>>>"


def build_triage_prompt(entrada: TriageInput, nonce: Callable[[], str]) -> str:
    """
    Prompt do usuário da triagem: contexto confiável primeiro, dado de terceiros delimitado.

    :param entrada: dados do artefato e do acervo.
    :param nonce: gerador de nonce (ex.: `secrets.token_hex(8)`).
    :return: texto enviado pelo stdin.
    :rtype: str
    """
    valor = _nonce(nonce, entrada.content, entrada.drafts_index)
    partes = [
        "# Contexto",
        f"Pasta: {entrada.alias} · Artefato: {entrada.path} · "
        f"Tipo pela convenção: {entrada.kind.value} · "
        f"Licença restrita: {'sim' if entrada.restricted_license else 'não'}",
        "## Critérios",
        entrada.criteria.strip(),
        "## Índice do acervo",
        entrada.library_index.strip() or "Acervo vazio.",
        "## Itens parecidos do acervo (mesmo tipo)",
    ]
    if entrada.similar:
        for item in entrada.similar:
            partes += [f"### {item.ref}", item.content.strip()]
    else:
        partes.append("Nenhum item parecido.")
    partes.append("## Rascunhos pendentes (id | tipo | nome | descrição)")
    if entrada.drafts_index.strip():
        partes.append(untrusted_block("RASCUNHOS_NAO_CONFIAVEIS", valor, entrada.drafts_index))
    else:
        partes.append("Nenhum rascunho pendente.")
    partes += [
        "## Artefato a triar",
        untrusted_block("ARTEFATO_NAO_CONFIAVEL", valor, entrada.content),
    ]
    return "\n\n".join(partes) + "\n"


def drafts_index(
    drafts: list[Draft], kind: ArtifactKind, artifact_path: str, artifact_text: str
) -> tuple[str, bool]:
    """
    Índice dos rascunhos pendentes para a triagem: só id, tipo, nome e descrição (FR-042).

    Acima de 64 KiB, entram primeiro os do mesmo tipo, depois os mais parecidos; desempate por
    id (FR-011b).

    :return: (texto, truncou).
    :rtype: tuple[str, bool]
    """
    cabeca = "\n".join(artifact_text.splitlines()[:_CABECA])
    alvo = tokens(f"{artifact_path} {cabeca}")

    def chave(d: Draft) -> tuple[int, float, str]:
        parecido = _jaccard(alvo, tokens(f"{d.proposal.name} {d.proposal.description}"))
        return (0 if d.proposal.kind is kind else 1, -parecido, d.draft_id)

    linhas = [
        f"{d.draft_id} | {d.proposal.kind.value} | {d.proposal.name} | "
        f"{' '.join(d.proposal.description.split())}"
        for d in sorted(drafts, key=chave)
    ]
    return truncate_index("".join(f"{linha}\n" for linha in linhas), INDEX_LIMIT)


@dataclass(frozen=True)
class DraftInput:
    """Tudo o que entra no prompt de rascunho de uma lacuna."""

    alias: str
    path: str
    kind: ArtifactKind
    source: str
    source_is_summary: bool
    merge_library: CatalogItem | None
    merge_draft: Draft | None
    regenerate: bool


def build_draft_prompt(entrada: DraftInput, nonce: Callable[[], str]) -> str:
    """
    Prompt do rascunho: fonte (original ou só o resumo — FR-016a) delimitada como não confiável.

    Fusão com item do acervo: o item entra como contexto confiável. Fusão com rascunho pendente:
    o rascunho (derivado de terceiros) entra delimitado como não confiável.
    """
    rascunho_existente = entrada.merge_draft.proposal.body if entrada.merge_draft else ""
    valor = _nonce(nonce, entrada.source, rascunho_existente)
    tipo = "resumo das ideias (licença restrita)" if entrada.source_is_summary else "artefato"
    partes = [
        "# Tarefa",
        f"Escreva um item do acervo a partir das ideias do {tipo} de "
        f"{entrada.alias} · {entrada.path} (tipo proposto: {entrada.kind.value}).",
    ]
    if entrada.regenerate:
        partes.append(
            "A proposta anterior ficou parecida demais com o original. Reescreva a partir das "
            "ideias, com estrutura, ordem e exemplos próprios."
        )
    if entrada.merge_library is not None:
        partes += [
            f"## Fusão com o item do acervo {entrada.merge_library.ref}",
            "Descreva o item resultante inteiro, integrando a ideia nova:",
            entrada.merge_library.content.strip(),
        ]
    if entrada.merge_draft is not None:
        partes += [
            f"## Fusão com o rascunho pendente {entrada.merge_draft.draft_id}",
            untrusted_block("RASCUNHO_NAO_CONFIAVEL", valor, rascunho_existente),
        ]
    partes += ["## Fonte", untrusted_block("ARTEFATO_NAO_CONFIAVEL", valor, entrada.source)]
    return "\n\n".join(partes) + "\n"


def build_judge_prompt(original: str, proposal: str, nonce: Callable[[], str]) -> str:
    """Prompt do juiz: ORIGINAL e PROPOSTA, ambos delimitados como não confiáveis (FR-017)."""
    valor = _nonce(nonce, original, proposal)
    return (
        "## ORIGINAL\n\n"
        + untrusted_block("ORIGINAL_NAO_CONFIAVEL", valor, original)
        + "\n\n## PROPOSTA\n\n"
        + untrusted_block("PROPOSTA_NAO_CONFIAVEL", valor, proposal)
        + "\n"
    )
