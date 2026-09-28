# -*- coding: utf-8 -*-
"""
NOME: curation_triage.py
TITULO: Veredito de triagem, elegibilidade e transições de etapa (feature 011)
DATA: 28/09/2026 15:54
MODIFICADO: 28/09/2026 15:54
VERSÃO: 0.1.0
DEPEND: (nenhuma — stdlib apenas; camada Domain)
HISTÓRICO:
    - 28/09/2026 15:54: criação (T013, feature 011) — faz test_curation_triage.py passar
STATUS: DEV
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from praxisforge.domain.curation_artifact import ArtifactKind, Stage, _FromStr
from praxisforge.domain.curation_state import ArtifactState
from praxisforge.domain.errors import InvalidTriageError

MAX_ATTEMPTS = 3
MAX_JUSTIFICATION = 2000
MAX_SUMMARY = 4000
MAX_COVERED_BY = 3
LIBRARY_REF = re.compile(r"^(skill|command|agent|hook|rule|reference)/[a-z0-9]+(-[a-z0-9]+)*$")
DRAFT_ID = re.compile(r"^[0-9a-f]{16}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TIPOS_DO_ACERVO = frozenset(
    {
        ArtifactKind.SKILL,
        ArtifactKind.COMMAND,
        ArtifactKind.AGENT,
        ArtifactKind.HOOK,
        ArtifactKind.RULE,
        ArtifactKind.REFERENCE,
    }
)
_NUNCA_ELEGIVEIS = frozenset({Stage.REVIEWED, Stage.PROMOTED, Stage.DISCARDED, Stage.REMOVED})


class TriageVerdict(_FromStr):
    """Veredito da triagem: já existe no acervo, falta no acervo ou não é curável (FR-012)."""

    COVERED = "covered"
    GAP = "gap"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class MergeTarget:
    """
    Alvo de uma fusão proposta (K3): item do acervo (`<tipo>/<nome>`) ou rascunho pendente.

    :param kind: `"library"` ou `"draft"`.
    :type kind: str
    :param ref: `<tipo>/<nome>` do acervo ou `draft_id` (16 hex).
    :type ref: str
    """

    kind: str
    ref: str

    def is_valid(self) -> bool:
        """
        Diz se o alvo tem formato aceito (nenhum campo vira caminho — FR-015a).

        :Example:

        >>> MergeTarget("draft", "0123456789abcdef").is_valid()
        True
        >>> MergeTarget("draft", "../x").is_valid()
        False
        """
        if self.kind == "library":
            return bool(LIBRARY_REF.match(self.ref))
        if self.kind == "draft":
            return bool(DRAFT_ID.match(self.ref))
        return False


@dataclass(frozen=True)
class Triage:
    """
    Resultado validado da triagem de um artefato (FR-012 a FR-015a, FR-023).

    :raises InvalidTriageError: qualquer regra do veredito violada.
    """

    verdict: TriageVerdict
    justification: str
    covered_by: tuple[str, ...]
    merge_target: MergeTarget | None
    suggested_kind: ArtifactKind | None
    ideas_summary: str | None
    prompt_fingerprint: str
    model: str
    cost_usd: Decimal | None
    triaged_at: datetime
    draft_id: str | None = None

    def __post_init__(self) -> None:
        self._check_texts()
        self._check_verdict()
        if self.suggested_kind is not None and self.suggested_kind not in _TIPOS_DO_ACERVO:
            raise InvalidTriageError(f"tipo sugerido inválido: {self.suggested_kind.value}")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise InvalidTriageError("custo negativo")
        if self.triaged_at.tzinfo is None:
            raise InvalidTriageError("data da triagem sem fuso horário")
        if not _SHA256.match(self.prompt_fingerprint):
            raise InvalidTriageError("impressão digital dos prompts inválida")
        if self.draft_id is not None and not DRAFT_ID.match(self.draft_id):
            raise InvalidTriageError("draft_id inválido")

    def _check_texts(self) -> None:
        if not self.justification.strip():
            raise InvalidTriageError("justificativa vazia")
        if len(self.justification) > MAX_JUSTIFICATION:
            raise InvalidTriageError("justificativa longa demais")
        if not self.model.strip():
            raise InvalidTriageError("modelo vazio")
        if self.ideas_summary is not None:
            if not self.ideas_summary.strip():
                raise InvalidTriageError("resumo de ideias vazio")
            if len(self.ideas_summary) > MAX_SUMMARY:
                raise InvalidTriageError("resumo de ideias longo demais")

    def _check_verdict(self) -> None:
        if self.verdict is TriageVerdict.COVERED:
            if not self.covered_by:
                raise InvalidTriageError("covered exige ao menos um item em covered_by")
        elif self.covered_by:
            raise InvalidTriageError("covered_by só vale para o veredito covered")
        if len(self.covered_by) > MAX_COVERED_BY:
            raise InvalidTriageError(f"covered_by aceita no máximo {MAX_COVERED_BY} itens")
        for ref in self.covered_by:
            if not LIBRARY_REF.match(ref):
                raise InvalidTriageError("covered_by fora do formato <tipo>/<nome>")
        if self.merge_target is not None:
            if self.verdict is not TriageVerdict.GAP:
                raise InvalidTriageError("fusão só vale para o veredito gap")
            if not self.merge_target.is_valid():
                raise InvalidTriageError("alvo de fusão inválido")


def validate_in_context(
    triage: Triage,
    artifact_kind: ArtifactKind,
    restricted_license: bool,
    library_has: Callable[[str], bool],
    draft_exists: Callable[[str], bool],
) -> None:
    """
    Regras que dependem do artefato e do acervo real, e não só da resposta (FR-012, FR-015,
    FR-016a).

    :param triage: veredito já validado isoladamente.
    :type triage: Triage
    :param artifact_kind: tipo do artefato pela convenção.
    :type artifact_kind: ArtifactKind
    :param restricted_license: licença da pasta `link`/`unknown`.
    :type restricted_license: bool
    :param library_has: consulta ao catálogo real do acervo (`<tipo>/<nome>`).
    :type library_has: Callable[[str], bool]
    :param draft_exists: consulta aos rascunhos pendentes (`draft_id`).
    :type draft_exists: Callable[[str], bool]
    :raises InvalidTriageError: item citado ou alvo inexistente; campo obrigatório ausente.
    """
    for ref in triage.covered_by:
        if not library_has(ref):
            raise InvalidTriageError(f"item citado inexistente no acervo: {ref}")
    alvo = triage.merge_target
    if alvo is not None:
        existe = library_has(alvo.ref) if alvo.kind == "library" else draft_exists(alvo.ref)
        if not existe:
            raise InvalidTriageError(f"alvo de fusão inexistente: {alvo.ref}")
    if triage.verdict is TriageVerdict.GAP:
        if artifact_kind is ArtifactKind.UNKNOWN and triage.suggested_kind is None:
            raise InvalidTriageError("tipo sugerido obrigatório para artefato unknown")
        if restricted_license and triage.ideas_summary is None:
            raise InvalidTriageError("resumo de ideias obrigatório (licença link/unknown)")


def is_eligible(
    state: ArtifactState, fingerprint: str, retry_failed: bool, max_attempts: int = MAX_ATTEMPTS
) -> bool:
    """
    Diz se o artefato vai para a triagem nesta execução (FR-002, FR-020).

    :param state: estado atual do artefato.
    :type state: ArtifactState
    :param fingerprint: impressão digital atual dos prompts.
    :type fingerprint: str
    :param retry_failed: incluir `failed` com tentativas esgotadas.
    :type retry_failed: bool
    :param max_attempts: limite de tentativas.
    :type max_attempts: int
    :return: True se elegível.
    :rtype: bool

    :Example:

    >>> from praxisforge.domain.curation_artifact import ArtifactKind, Stage
    >>> is_eligible(ArtifactState(ArtifactKind.SKILL, "a" * 64, Stage.PENDING), "f" * 64, False)
    True
    """
    if state.stage in _NUNCA_ELEGIVEIS:
        return False
    if state.stage is Stage.PENDING:
        return True
    prompts_mudaram = state.triage is None or state.triage.prompt_fingerprint != fingerprint
    if state.stage is Stage.FAILED:
        esgotado = state.attempts >= max_attempts
        return retry_failed or not esgotado or (state.triage is not None and prompts_mudaram)
    return prompts_mudaram


def with_triage(state: ArtifactState, triage: Triage) -> ArtifactState:
    """Grava o veredito e avança para `triaged` (limpa o último erro)."""
    return replace(state, stage=Stage.TRIAGED, triage=triage, last_error=None)


def with_draft(state: ArtifactState, draft_id: str) -> ArtifactState:
    """
    Registra o rascunho gravado e avança para `drafted`.

    :raises InvalidTriageError: artefato sem veredito `gap`.
    """
    if state.triage is None or state.triage.verdict is not TriageVerdict.GAP:
        raise InvalidTriageError("rascunho só existe para artefato triado como gap")
    return replace(state, stage=Stage.DRAFTED, triage=replace(state.triage, draft_id=draft_id))


def with_failure(state: ArtifactState, error_type: str) -> ArtifactState:
    """Marca `failed` com o tipo do erro e soma uma tentativa (a triagem gravada é mantida)."""
    return replace(state, stage=Stage.FAILED, last_error=error_type, attempts=state.attempts + 1)
