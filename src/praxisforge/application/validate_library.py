# -*- coding: utf-8 -*-
"""
NOME: validate_library.py
TITULO: Caso de uso — validar o acervo library/ (forma por tipo + proveniência)
DATA: 25/09/2026 13:09
MODIFICADO: 25/09/2026 13:09
VERSÃO: 0.1.0
DEPEND: praxisforge.domain, praxisforge.application.ports, praxisforge.application.validate_sources
HISTÓRICO:
    - 25/09/2026 13:09: criação (T018, feature 009) — sucede validate_skills.py
STATUS: DEV
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import ContractValidator, LibraryRepository, SourceReader
from praxisforge.application.validate_sources import validate_sources
from praxisforge.domain.errors import (
    ContractValidationError,
    InvalidLibraryItemError,
    LibraryNotFoundError,
    PraxisForgeError,
    Violation,
)
from praxisforge.domain.library_item import ItemKind as ItemKind  # reexportado p/ a CLI
from praxisforge.domain.library_item import LibraryItem

logger = logging.getLogger(__name__)

UNKNOWN_KIND = "?"


def schema_for(kind: ItemKind) -> str:
    """
    Nome do contrato do frontmatter do tipo.

    :param kind: tipo.
    :type kind: ItemKind
    :return: nome do schema (sem `.json`).
    :rtype: str

    :Example:

    >>> schema_for(ItemKind.HOOK)
    'hook-frontmatter-v1'
    """
    return f"{kind.value}-frontmatter-v1"


@dataclass(frozen=True)
class ItemFailure:
    """Falha de um item: tipo (`?` quando desconhecido), nome, tipo da exceção e motivos."""

    kind: str
    name: str
    error_type: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class LibraryValidationReport:
    """Itens válidos e falhas por item, na ordem (tipo, nome)."""

    ok: list[LibraryItem]
    failures: list[ItemFailure]

    @property
    def rewrite_pending(self) -> list[LibraryItem]:
        """Itens válidos marcados para reescrita (FR-024, informativo)."""
        return [item for item in self.ok if item.rewrite_pending]


@dataclass
class _IndiceDeFontes:
    """Slug → arquivos; cada fonte é avaliada uma única vez por lote (research R8)."""

    reader: SourceReader
    validator: ContractValidator
    por_slug: dict[str, list[Path]]
    cache: dict[str, Violation | None] = field(default_factory=dict)

    def violacao(self, slug: str) -> Violation | None:
        """Violação que impede usar a fonte, ou None quando válida."""
        if slug not in self.cache:
            self.cache[slug] = self._avaliar(slug)
        return self.cache[slug]

    def _avaliar(self, slug: str) -> Violation | None:
        arquivos = self.por_slug.get(slug, [])
        if not arquivos:
            return Violation("metadata.sources", f"fonte '{slug}' não encontrada")
        if len(arquivos) > 1:
            return Violation("metadata.sources", f"slug ambíguo '{slug}' (mais de uma categoria)")
        report = validate_sources(self.reader, self.validator, arquivos)
        if report.failures:
            return Violation(
                "metadata.sources", f"fonte '{slug}' inválida: {report.failures[0].message}"
            )
        return None


@dataclass
class _Validacao:
    repository: LibraryRepository
    validator: ContractValidator
    fontes: _IndiceDeFontes
    references: dict[str, Violation | None] = field(default_factory=dict)

    def item(self, kind: ItemKind, name: str) -> LibraryItem:
        documento = self.repository.load(kind, name)
        violacoes: list[Violation] = []
        item: LibraryItem | None = None
        try:
            item = LibraryItem.from_parts(
                kind, name, documento.frontmatter, documento.support_files, documento.missing_files
            )
        except InvalidLibraryItemError as error:
            violacoes.extend(error.violations)
        try:
            self.validator.validate(documento.frontmatter, schema_name=schema_for(kind))
        except ContractValidationError as error:
            ja_citados = {v.field for v in violacoes}
            violacoes.extend(v for v in error.violations if v.field not in ja_citados)
        if item is not None:
            violacoes.extend(v for s in item.sources if (v := self.fontes.violacao(s)))
            violacoes.extend(v for r in item.references if (v := self._reference(r)))
        if violacoes or item is None:
            raise InvalidLibraryItemError(kind.value, name, violacoes)
        return item

    def _reference(self, name: str) -> Violation | None:
        if name not in self.references:
            self.references[name] = self._avaliar_reference(name)
        return self.references[name]

    def _avaliar_reference(self, name: str) -> Violation | None:
        if name not in self.repository.list_entries(ItemKind.REFERENCE):
            return Violation("metadata.references", f"reference '{name}' não encontrada")
        try:
            self.item(ItemKind.REFERENCE, name)
        except PraxisForgeError:
            return Violation("metadata.references", f"reference '{name}' inválida")
        return None


def _falha(kind: str, name: str, error: PraxisForgeError) -> ItemFailure:
    if isinstance(error, InvalidLibraryItemError):
        motivos = tuple(f"{v.field}: {v.reason}" for v in error.violations)
    else:
        motivos = (str(error),)
    return ItemFailure(kind, name, type(error).__name__, motivos)


def validate_library(
    repository: LibraryRepository,
    validator: ContractValidator,
    source_reader: SourceReader,
    source_paths: Sequence[Path],
    kind: ItemKind | None = None,
    name: str | None = None,
) -> LibraryValidationReport:
    """
    Valida o acervo inteiro, um tipo ou um item; a falha de um item não interrompe o lote.

    :param repository: porta de leitura do acervo.
    :type repository: LibraryRepository
    :param validator: validação contra `<tipo>-frontmatter-v1` e `source-schema-v3`.
    :type validator: ContractValidator
    :param source_reader: leitura do frontmatter das fontes.
    :type source_reader: SourceReader
    :param source_paths: todos os registros de fonte (`src/data/sources/**/*.md`).
    :type source_paths: Sequence[Path]
    :param kind: tipo pedido; None = todos (e entradas desconhecidas viram falha).
    :type kind: ItemKind | None
    :param name: item pedido (exige `kind`); None = todos do tipo.
    :type name: str | None
    :return: itens válidos e falhas por item.
    :rtype: LibraryValidationReport
    :raises LibraryNotFoundError: `library/` ausente (erro de ambiente, não do item).
    """
    por_slug: dict[str, list[Path]] = {}
    for path in sorted(source_paths):
        por_slug.setdefault(path.stem, []).append(path)
    validacao = _Validacao(
        repository, validator, _IndiceDeFontes(source_reader, validator, por_slug)
    )
    ok: list[LibraryItem] = []
    failures: list[ItemFailure] = []
    tipos = [kind] if kind is not None else list(ItemKind)
    for tipo in tipos:
        nomes = [name] if name is not None else repository.list_entries(tipo)
        for nome in nomes:
            try:
                ok.append(validacao.item(tipo, nome))
            except LibraryNotFoundError:
                raise
            except PraxisForgeError as error:
                failures.append(_falha(tipo.value, nome, error))
    if kind is None:
        for entrada in repository.unknown_entries():
            failures.append(
                ItemFailure(UNKNOWN_KIND, entrada, "UnknownItemKindError", ("tipo desconhecido",))
            )
    log_event(
        logger,
        event="validate_library",
        alias="*",
        outcome=f"{len(ok)} ok, {len(failures)} com falha",
        error_type=None,
    )
    return LibraryValidationReport(ok=ok, failures=failures)
