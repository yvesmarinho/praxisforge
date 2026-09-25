# -*- coding: utf-8 -*-
"""
NOME: publish_items.py
TITULO: Caso de uso — publicar itens do acervo em pastas de projeto (idempotente)
DATA: 25/09/2026 13:18
MODIFICADO: 25/09/2026 13:18
VERSÃO: 0.1.0
DEPEND: praxisforge.application.validate_library, praxisforge.application.ports
HISTÓRICO:
    - 25/09/2026 13:18: criação (T036, feature 009) — sucede publish_skills.py; só projetos,
      skill/command/agent/rule, references dentro da skill, marcador da 008 regravado
STATUS: DEV
"""

import hashlib
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    ContractValidator,
    ItemPublisher,
    LibraryRepository,
    PublishedState,
    SourceReader,
)
from praxisforge.application.validate_library import UNKNOWN_KIND, validate_library
from praxisforge.domain.errors import (
    ForeignSkillDestinationError,
    NotPublishableKindError,
    PraxisForgeError,
    SkillPublicationError,
    SkillVersionNotBumpedError,
)
from praxisforge.domain.library_item import ItemKind, LibraryItem

logger = logging.getLogger(__name__)

MODES = ("copy", "symlink")
_NOSSOS = ("copy", "symlink", "broken_symlink")


@dataclass(frozen=True)
class PublishOutcome:
    """Resultado por item (`<tipo>/<nome>`): publicada, atualizada, inalterada,
    marcador atualizado ou recusada (com motivo)."""

    name: str
    status: str
    reason: str = ""
    error_type: str | None = None


@dataclass(frozen=True)
class PublishReport:
    """Resultados por item, órfãos encontrados e órfãos removidos (`<tipo>/<nome>`)."""

    outcomes: list[PublishOutcome]
    orphans: list[str]
    removed: list[str]

    @property
    def environment_failure(self) -> bool:
        """Houve falha de gravação (exit 3)."""
        return any(o.error_type == SkillPublicationError.__name__ for o in self.outcomes)

    @property
    def refused(self) -> bool:
        """Algum item foi recusado (exit 1)."""
        return any(o.status == "recusada" for o in self.outcomes)


def _chave(kind: ItemKind, name: str) -> str:
    return f"{kind.value}/{name}"


def _hash_publicado(repository: LibraryRepository, item: LibraryItem) -> str:
    """Hash do item; com references, combina os hashes (sem references = hash da 008)."""
    base = repository.content_hash(item.kind, item.name)
    if not item.references:
        return base
    digest = hashlib.sha256(base.encode("ascii"))
    for referencia in sorted(item.references):
        digest.update(referencia.encode("utf-8"))
        digest.update(repository.content_hash(ItemKind.REFERENCE, referencia).encode("ascii"))
    return digest.hexdigest()


def _publicar_um(
    repository: LibraryRepository,
    publisher: ItemPublisher,
    project: Path,
    item: LibraryItem,
    mode: str,
) -> PublishOutcome:
    chave = _chave(item.kind, item.name)
    estado: PublishedState = publisher.inspect(project, item.kind, item.name)
    if estado.kind == "foreign":
        raise ForeignSkillDestinationError(chave, str(project / ".claude" / item.kind.directory))
    novo = "publicada" if estado.kind == "absent" else "atualizada"
    if mode == "symlink":
        if estado.kind == "symlink":
            return PublishOutcome(chave, "inalterada")
        publisher.publish_symlink(project, item.kind, item.name)
        return PublishOutcome(chave, novo)
    content_hash = _hash_publicado(repository, item)
    if estado.kind == "copy":
        if estado.content_sha256 == content_hash:
            if estado.legacy_marker:
                publisher.rewrite_marker(
                    project, item.kind, item.name, str(estado.version), content_hash
                )
                return PublishOutcome(chave, "marcador atualizado")
            return PublishOutcome(chave, "inalterada")
        if estado.version == item.version:
            raise SkillVersionNotBumpedError(chave, item.version)
    referencias = [repository.item_path(ItemKind.REFERENCE, r) for r in item.references]
    publisher.publish_copy(project, item.kind, item.name, item.version, content_hash, referencias)
    return PublishOutcome(chave, novo)


def publish_items(
    repository: LibraryRepository,
    validator: ContractValidator,
    source_reader: SourceReader,
    source_paths: Sequence[Path],
    publisher: ItemPublisher,
    project: Path,
    *,
    kind: ItemKind | None = None,
    name: str | None = None,
    mode: str = "copy",
    prune: bool = False,
) -> PublishReport:
    """
    Valida e publica itens num projeto; a falha de um item não interrompe o lote.

    Sem `kind`/`name` publica todos os tipos publicáveis e calcula órfãos. Troca de modo
    (cópia ↔ symlink) entre destinos nossos sempre publica, sem regra de versão.

    :param repository: porta de leitura do acervo.
    :type repository: LibraryRepository
    :param validator: validação dos contratos.
    :type validator: ContractValidator
    :param source_reader: leitura das fontes.
    :type source_reader: SourceReader
    :param source_paths: registros de fonte disponíveis.
    :type source_paths: Sequence[Path]
    :param publisher: porta de publicação.
    :type publisher: ItemPublisher
    :param project: pasta do projeto de destino.
    :type project: Path
    :param kind: tipo do item pedido (com `name`); None = todos os publicáveis.
    :type kind: ItemKind | None
    :param name: item pedido.
    :type name: str | None
    :param mode: `copy` ou `symlink`.
    :type mode: str
    :param prune: remove órfãos nossos (só sem `kind`/`name`).
    :type prune: bool
    :return: resultado por item, órfãos e removidos.
    :rtype: PublishReport
    :raises NotPublishableKindError: tipo pedido não é publicável (hook, reference).
    :raises ValueError: modo desconhecido (erro da fronteira).
    """
    if mode not in MODES:
        raise ValueError(f"modo de publicação desconhecido: {mode}")
    if kind is not None and not kind.publishable:
        raise NotPublishableKindError(
            kind.value, "hooks e references não são publicados (references vão dentro da skill)"
        )
    report = validate_library(
        repository, validator, source_reader, source_paths, kind=kind, name=name
    )
    publicaveis = {k.value for k in ItemKind if k.publishable}
    outcomes = [
        PublishOutcome(f"{f.kind}/{f.name}", "recusada", "; ".join(f.reasons), f.error_type)
        for f in report.failures
        if f.kind in publicaveis and f.kind != UNKNOWN_KIND
    ]
    for item in report.ok:
        if not item.kind.publishable:
            continue
        try:
            outcomes.append(_publicar_um(repository, publisher, project, item, mode))
        except PraxisForgeError as error:
            outcomes.append(
                PublishOutcome(
                    _chave(item.kind, item.name), "recusada", str(error), type(error).__name__
                )
            )

    ordem = {k.value: posicao for posicao, k in enumerate(ItemKind)}
    outcomes.sort(key=lambda o: (ordem.get(o.name.split("/", 1)[0], 99), o.name))

    orphans: list[str] = []
    removed: list[str] = []
    if kind is None and name is None:
        for tipo in (k for k in ItemKind if k.publishable):
            existentes = set(repository.list_entries(tipo))
            for publicado in publisher.list_published(project, tipo):
                if publicado in existentes:
                    continue
                orphans.append(_chave(tipo, publicado))
                if not prune:
                    continue
                try:
                    publisher.remove(project, tipo, publicado)
                    removed.append(_chave(tipo, publicado))
                except PraxisForgeError as error:
                    outcomes.append(
                        PublishOutcome(
                            _chave(tipo, publicado), "recusada", str(error), type(error).__name__
                        )
                    )
    for outcome in outcomes:
        log_event(
            logger,
            event="publish_item",
            alias=outcome.name,
            outcome=outcome.status,
            error_type=outcome.error_type,
        )
    return PublishReport(outcomes=outcomes, orphans=orphans, removed=removed)
