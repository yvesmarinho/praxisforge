# -*- coding: utf-8 -*-
"""
NOME: build_index.py
TITULO: Caso de uso — gerar o índice do acervo (library/INDEX.md) determinístico
DATA: 25/09/2026 13:15
MODIFICADO: 25/09/2026 13:15
VERSÃO: 0.1.0
DEPEND: praxisforge.application.validate_library, praxisforge.application.ports
HISTÓRICO:
    - 25/09/2026 13:15: criação (T030, feature 009) — sucede build_catalog.py
STATUS: DEV
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    ContractValidator,
    IndexWriter,
    LibraryRepository,
    SourceReader,
)
from praxisforge.application.validate_library import ItemFailure, validate_library
from praxisforge.domain.library_item import ItemKind, LibraryItem

logger = logging.getLogger(__name__)

_CABECALHO = (
    "<!-- Arquivo gerado por `praxisforge library index` — não editar à mão. -->\n"
    "\n"
    "# Índice do acervo\n"
    "\n"
    "Acervo versionado em `library/`, um diretório por tipo de recurso. Para criar um item, "
    "parta de `library/_templates/`.\n"
)
_TITULOS = {
    ItemKind.SKILL: "Skills",
    ItemKind.COMMAND: "Commands",
    ItemKind.AGENT: "Agents",
    ItemKind.HOOK: "Hooks",
    ItemKind.RULE: "Rules",
    ItemKind.REFERENCE: "References",
}
_PENDENTE = " ⚠ reescrita pendente"


@dataclass(frozen=True)
class IndexResult:
    """Itens indexados (`<tipo>/<nome>`, na ordem do índice) e itens omitidos por falha."""

    items: list[str]
    omitted: list[ItemFailure]


def _celula(texto: str) -> str:
    return " ".join(texto.split()).replace("|", "\\|")


def _caminho(item: LibraryItem) -> str:
    sufixo = "/" if item.kind.is_folder else ".md"
    return f"`library/{item.kind.directory}/{item.name}{sufixo}`"


def render_index(items: Sequence[LibraryItem]) -> str:
    """
    Monta o Markdown do índice, sem data de geração (determinístico).

    :param items: itens válidos, em qualquer ordem.
    :type items: Sequence[LibraryItem]
    :return: conteúdo completo de `library/INDEX.md`.
    :rtype: str

    :Example:

    >>> "Nenhum item." in render_index([])
    True
    """
    partes = [_CABECALHO]
    for kind in ItemKind:
        partes.append(f"\n## {_TITULOS[kind]}\n\n")
        do_tipo = sorted((i for i in items if i.kind is kind), key=lambda i: i.name)
        if not do_tipo:
            partes.append("Nenhum item.\n")
            continue
        linhas = [
            "| Nome | Ideia central | Versão | Fontes | Caminho |",
            "|---|---|---|---|---|",
        ]
        for item in do_tipo:
            nome = item.name + (_PENDENTE if item.rewrite_pending else "")
            fontes = ", ".join(sorted(item.sources)) if item.sources else "autoral"
            linhas.append(
                f"| {nome} | {_celula(item.description)} | {item.version} "
                f"| {fontes} | {_caminho(item)} |"
            )
        partes.append("\n".join(linhas) + "\n")
    return "".join(partes)


def build_index(
    repository: LibraryRepository,
    validator: ContractValidator,
    source_reader: SourceReader,
    source_paths: Sequence[Path],
    writer: IndexWriter,
) -> IndexResult:
    """
    Valida o acervo, grava o índice só com os itens válidos e informa os omitidos.

    :param repository: porta de leitura do acervo.
    :type repository: LibraryRepository
    :param validator: validação dos contratos.
    :type validator: ContractValidator
    :param source_reader: leitura das fontes.
    :type source_reader: SourceReader
    :param source_paths: registros de fonte disponíveis.
    :type source_paths: Sequence[Path]
    :param writer: gravação atômica do índice.
    :type writer: IndexWriter
    :return: itens indexados e omitidos.
    :rtype: IndexResult
    :raises IndexWriteError: falha ao gravar; o índice anterior permanece.
    :raises LibraryNotFoundError: `library/` ausente.
    """
    report = validate_library(repository, validator, source_reader, source_paths)
    writer.write(render_index(report.ok))
    ordem = {kind: posicao for posicao, kind in enumerate(ItemKind)}
    itens = [
        f"{i.kind.value}/{i.name}" for i in sorted(report.ok, key=lambda i: (ordem[i.kind], i.name))
    ]
    log_event(
        logger,
        event="build_index",
        alias="*",
        outcome=f"{len(itens)} itens, {len(report.failures)} omitidos",
        error_type=None,
    )
    return IndexResult(items=itens, omitted=report.failures)
