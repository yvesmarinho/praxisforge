# -*- coding: utf-8 -*-
"""
NOME: curation_draft.py
TITULO: Rascunho de item do acervo em staging — proposta, origens e verificações (feature 011)
DATA: 28/09/2026 16:16
MODIFICADO: 28/09/2026 16:16
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 28/09/2026 16:16: criação (T038, feature 011) — faz test_curation_draft.py passar
STATUS: DEV
"""

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from praxisforge.domain.curation_artifact import ArtifactKind, validate_relative_path
from praxisforge.domain.curation_triage import DRAFT_ID, MergeTarget
from praxisforge.domain.errors import InvalidCurationArtifactError, InvalidTriageError
from praxisforge.domain.structure_similarity import SimilarityCheck

MAX_DESCRIPTION = 1024
MAX_BODY = 65536
_NOME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TIPOS = frozenset(
    {
        ArtifactKind.SKILL,
        ArtifactKind.COMMAND,
        ArtifactKind.AGENT,
        ArtifactKind.HOOK,
        ArtifactKind.RULE,
        ArtifactKind.REFERENCE,
    }
)


def draft_id_for(alias: str, path: str) -> str:
    """
    Id estável do rascunho: 16 hex do SHA-256 de `alias\\0caminho` da 1ª origem (R8).

    :Example:

    >>> len(draft_id_for("demo_a", "skills/x"))
    16
    """
    return hashlib.sha256(f"{alias}\0{path}".encode()).hexdigest()[:16]


@dataclass(frozen=True)
class DraftProposal:
    """
    Proposta de item do acervo escrita pelo modelo de rascunho (só ideias — FR-016).

    :raises InvalidTriageError: tipo fora do acervo, nome fora de kebab-case, texto vazio ou longo.
    """

    kind: ArtifactKind
    name: str
    description: str
    body: str

    def __post_init__(self) -> None:
        if self.kind not in _TIPOS:
            raise InvalidTriageError(f"tipo de rascunho fora do acervo: {self.kind.value}")
        if not (3 <= len(self.name) <= 64 and _NOME.match(self.name)):
            raise InvalidTriageError("nome do rascunho fora de kebab-case (3 a 64)")
        if not self.description.strip() or len(self.description) > MAX_DESCRIPTION:
            raise InvalidTriageError("descrição do rascunho vazia ou longa demais")
        if not self.body.strip() or len(self.body.encode("utf-8")) > MAX_BODY:
            raise InvalidTriageError("corpo do rascunho vazio ou acima de 64 KiB")


@dataclass(frozen=True)
class DraftOrigin:
    """Artefato de origem de um rascunho: alias, caminho relativo e hash triado."""

    alias: str
    path: str
    sha256: str


@dataclass(frozen=True)
class Draft:
    """
    Rascunho em `curation/_drafts/`, possivelmente com várias origens (fusão — FR-014).

    :raises InvalidTriageError: origens vazias ou repetidas, checks fora de 1–2, id, alvo,
        custo ou data inválidos.
    """

    draft_id: str
    proposal: DraftProposal
    origins: tuple[DraftOrigin, ...]
    checks: tuple[SimilarityCheck, ...]
    merge_target: MergeTarget | None
    prompt_fingerprint: str
    model: str
    cost_usd: Decimal | None
    updated_at: datetime

    def __post_init__(self) -> None:
        if not DRAFT_ID.match(self.draft_id):
            raise InvalidTriageError("draft_id inválido")
        if not self.origins:
            raise InvalidTriageError("rascunho sem origem")
        chaves = [(o.alias, o.path) for o in self.origins]
        if len(set(chaves)) != len(chaves):
            raise InvalidTriageError("origem repetida no rascunho")
        for origem in self.origins:
            try:
                validate_relative_path(origem.path)
            except InvalidCurationArtifactError as error:
                raise InvalidTriageError(f"origem inválida: {error}") from error
            if not _SHA256.match(origem.sha256):
                raise InvalidTriageError("hash da origem inválido")
        if not 1 <= len(self.checks) <= 2:
            raise InvalidTriageError("rascunho precisa de 1 ou 2 verificações de similaridade")
        if self.merge_target is not None and not self.merge_target.is_valid():
            raise InvalidTriageError("alvo de fusão inválido")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise InvalidTriageError("custo negativo")
        if self.updated_at.tzinfo is None:
            raise InvalidTriageError("data do rascunho sem fuso horário")
        if not _SHA256.match(self.prompt_fingerprint) or not self.model.strip():
            raise InvalidTriageError("impressão digital ou modelo inválido")

    @property
    def similarity_alert(self) -> bool:
        """Alerta = última verificação sinalizada (após a regeneração, se houve — FR-018)."""
        return self.checks[-1].flagged

    def with_origin(self, origin: DraftOrigin) -> "Draft":
        """Acrescenta a origem, ou substitui a de mesmo alias e caminho (FR-025)."""
        chave = (origin.alias, origin.path)
        if chave not in {(o.alias, o.path) for o in self.origins}:
            return replace(self, origins=(*self.origins, origin))
        novas = tuple(origin if (o.alias, o.path) == chave else o for o in self.origins)
        return replace(self, origins=novas)
