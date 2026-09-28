# -*- coding: utf-8 -*-
"""
NOME: triage_folders.py
TITULO: Caso de uso — triagem com LLM dos artefatos inventariados (lote tolerante, com teto)
DATA: 28/09/2026 16:03
MODIFICADO: 28/09/2026 16:20
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports, praxisforge.domain
HISTÓRICO:
    - 28/09/2026 16:03: criação — US1 (T030, feature 011)
    - 28/09/2026 16:20: US2 — rascunho, similaridade em duas camadas, regeneração, fusões (T040)
STATUS: DEV
"""

import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from praxisforge.application.logging_events import log_event
from praxisforge.application.ports import (
    ArtifactReader,
    CatalogItem,
    CurationStore,
    DraftStore,
    FolderLocator,
    FolderRegistryRepository,
    LanguageModel,
    LibraryCatalog,
    ModelReply,
    ModelRequest,
    ModelRole,
    PromptSource,
)
from praxisforge.application.resolve_folder_path import ItemFailure
from praxisforge.application.triage_budget import (
    DRAFT_WORST_CASE_CALLS,
    TRIAGE_CALLS,
    TriageBudget,
)
from praxisforge.application.triage_context import (
    INDEX_LIMIT,
    DraftInput,
    TriageInput,
    build_draft_prompt,
    build_judge_prompt,
    build_triage_prompt,
    drafts_index,
    select_similar,
    truncate_index,
)
from praxisforge.domain.curation_artifact import ArtifactKind, Stage
from praxisforge.domain.curation_draft import Draft, DraftOrigin, DraftProposal, draft_id_for
from praxisforge.domain.curation_state import ArtifactState
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.curation_triage import (
    MergeTarget,
    Triage,
    TriageVerdict,
    is_eligible,
    validate_in_context,
    with_draft,
    with_failure,
    with_triage,
)
from praxisforge.domain.errors import (
    ArtifactTooLargeError,
    CurationNotInventoriedError,
    FolderPathInvalidError,
    InvalidTriageError,
    InvalidTriageOptionsError,
    LanguageModelResponseInvalidError,
    LanguageModelTimeoutError,
    LanguageModelUnavailableError,
    PraxisForgeError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.library_item import ItemKind
from praxisforge.domain.license_policy import ExtractPolicy, max_policy
from praxisforge.domain.prompt_set import PromptSet
from praxisforge.domain.structure_similarity import (
    SimilarityCheck,
    skeleton_of,
    structural_score,
)

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("America/Sao_Paulo")
_TRIAGE_SCHEMA = "curation-triage-response-v1"
_DRAFT_SCHEMA = "curation-draft-response-v1"
_JUDGE_SCHEMA = "curation-judge-response-v1"
_INDISPONIBILIDADE = (LanguageModelTimeoutError, LanguageModelUnavailableError)
_FALHAS_DO_ARTEFATO = (
    *_INDISPONIBILIDADE,
    LanguageModelResponseInvalidError,
    InvalidTriageError,
    ArtifactTooLargeError,
    FolderPathInvalidError,
)


@dataclass(frozen=True)
class TriageOptions:
    """Opções de uma execução (contrato da CLI; padrões do research R3, R10, R12)."""

    triage_model: str = "haiku"
    draft_model: str = "sonnet"
    timeout_s: int = 120
    similarity_threshold: float = 0.7
    retry_failed: bool = False
    max_consecutive_failures: int = 5
    max_calls: int = 50
    max_cost_usd: Decimal | None = None

    def __post_init__(self) -> None:
        if self.timeout_s < 10:
            raise InvalidTriageOptionsError("--timeout precisa ser ≥ 10")
        if not 0 < self.similarity_threshold <= 1:
            raise InvalidTriageOptionsError("--similarity-threshold precisa estar em (0, 1]")
        if self.max_consecutive_failures < 1:
            raise InvalidTriageOptionsError("--max-consecutive-failures precisa ser ≥ 1")
        TriageBudget(self.max_calls, self.max_cost_usd)  # valida os tetos


@dataclass(frozen=True)
class TriageDeps:
    """Dependências compostas pela Presentation (portas)."""

    repository: FolderRegistryRepository
    locator: FolderLocator
    store: CurationStore
    model: LanguageModel
    prompts: PromptSource
    catalog: LibraryCatalog
    reader: ArtifactReader
    drafts: DraftStore | None = None  # None desliga os rascunhos


@dataclass(frozen=True)
class ArtifactFailure:
    """Falha de um artefato: caminho relativo e tipo do erro."""

    path: str
    error_type: str


@dataclass
class FolderTriageResult:
    """Resultado da triagem de uma pasta."""

    alias: str
    verdicts: dict[str, int] = field(default_factory=lambda: {v.value: 0 for v in TriageVerdict})
    drafts: int = 0
    drafts_alerted: int = 0
    failures: list[ArtifactFailure] = field(default_factory=list)
    remaining: int = 0

    @property
    def triaged(self) -> int:
        """Total de vereditos gravados nesta execução."""
        return sum(self.verdicts.values())


@dataclass
class TriageReport:
    """Relatório da execução: por pasta, falhas de pasta, custo e motivo de parada."""

    folders: list[FolderTriageResult] = field(default_factory=list)
    failures: list[ItemFailure] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    calls: int = 0
    cost: Decimal = Decimal("0")
    cost_measurable: bool = True
    stop_reason: str = "done"  # done | budget | consecutive_failures
    partial_dedupe: bool = False

    @property
    def has_failures(self) -> bool:
        """Alguma pasta ou artefato falhou."""
        return bool(self.failures) or any(p.failures for p in self.folders)


def _restrita(licenca: str) -> bool:
    """Licença `link`/`unknown` (FR-016a): o rascunho só vê o resumo das ideias."""
    return max_policy(licenca) is ExtractPolicy.LINK


def _item_kind(kind: ArtifactKind) -> ItemKind | None:
    try:
        return ItemKind(kind.value)
    except ValueError:
        return None


class _Execucao:
    """Estado mutável de uma execução (orçamento, falhas seguidas, relatório)."""

    def __init__(
        self,
        deps: TriageDeps,
        options: TriageOptions,
        prompts: PromptSet,
        now: Callable[[], datetime],
    ) -> None:
        self.deps = deps
        self.options = options
        self.prompts = prompts
        self.now = now
        self.budget = TriageBudget(options.max_calls, options.max_cost_usd)
        self.report = TriageReport()
        self.consecutivas = 0
        self.indice, truncou = truncate_index(deps.catalog.index_text(), INDEX_LIMIT)
        self.report.partial_dedupe = truncou
        # rascunho corrompido interrompe antes da 1ª chamada (FR-044)
        self.pendentes: list[Draft] = deps.drafts.list_pending() if deps.drafts else []

    @staticmethod
    def _nonce() -> str:
        return secrets.token_hex(8)

    # --- chamadas ao modelo -----------------------------------------------------------------

    def chamar(
        self, role: ModelRole, model: str, system: str, user: str, schema: str
    ) -> ModelReply:
        """Uma chamada contabilizada no orçamento (com ou sem sucesso)."""
        pedido = ModelRequest(
            role=role,
            model=model,
            system_prompt=system,
            user_prompt=user,
            response_schema=schema,
            timeout_s=self.options.timeout_s,
            max_budget_usd=self.budget.remaining_usd(),
        )
        try:
            resposta = self.deps.model.complete(pedido)
        except PraxisForgeError:
            self.budget.record_failed_call()
            raise
        self.budget.record(resposta.cost_usd)
        return resposta

    # --- pasta -----------------------------------------------------------------------------

    def pasta(self, folder: Folder) -> FolderTriageResult:
        alias = folder.alias.value
        caminho = self.deps.locator.check(alias, Path(folder.path))
        resultado = FolderTriageResult(alias=alias)
        with self.deps.store.lock(alias):
            estado = self.deps.store.load_state(alias)
            if estado is None:
                raise CurationNotInventoriedError(alias)
            for path in sorted(estado.artifacts):
                atual = estado.artifacts[path]
                if not self._elegivel(atual):
                    continue
                if self.report.stop_reason != "done" or not self.budget.can_spend(TRIAGE_CALLS):
                    if self.report.stop_reason == "done":
                        self.report.stop_reason = "budget"
                    resultado.remaining += 1
                    continue
                novo = self._artefato(folder, caminho, path, atual, resultado)
                estado = replace(
                    estado, artifacts={**estado.artifacts, path: novo}, updated_at=self.now()
                )
                self.deps.store.save_state(estado)
                if self.consecutivas >= self.options.max_consecutive_failures:
                    self.report.stop_reason = "consecutive_failures"
        log_event(logger, "triage_folder", alias, "ok", None)
        return resultado

    def _elegivel(self, estado: ArtifactState) -> bool:
        elegivel = is_eligible(estado, self.prompts.fingerprint, self.options.retry_failed)
        return elegivel or self._so_rascunho(estado)

    def _so_rascunho(self, estado: ArtifactState) -> bool:
        """Lacuna já triada com os prompts atuais e ainda sem rascunho (R10 revisto)."""
        t = estado.triage
        return (
            self.deps.drafts is not None
            and estado.stage is Stage.TRIAGED
            and t is not None
            and t.verdict is TriageVerdict.GAP
            and t.draft_id is None
            and t.prompt_fingerprint == self.prompts.fingerprint
        )

    # --- artefato --------------------------------------------------------------------------

    def _artefato(
        self,
        folder: Folder,
        caminho: Path,
        path: str,
        atual: ArtifactState,
        resultado: FolderTriageResult,
    ) -> ArtifactState:
        alias = folder.alias.value
        so_rascunho = self._so_rascunho(atual)
        try:
            conteudo = self.deps.reader.read(caminho, path)
            triagem = None if so_rascunho else self._triar(folder, path, atual.kind, conteudo)
        except _FALHAS_DO_ARTEFATO as error:
            return self._falha(alias, path, atual, error, resultado)
        if triagem is not None:
            self.consecutivas = 0
            resultado.verdicts[triagem.verdict.value] += 1
            log_event(logger, "triage_artifact", alias, triagem.verdict.value, None)
            atual = with_triage(atual, triagem)
        if not self._so_rascunho(atual):
            return atual
        if not self.budget.can_spend(DRAFT_WORST_CASE_CALLS):
            self.report.stop_reason = "budget"
            resultado.remaining += 1
            return atual
        try:
            rascunho = self._rascunhar(folder, path, atual, conteudo)
        except _FALHAS_DO_ARTEFATO as error:
            return self._falha(alias, path, atual, error, resultado)
        self.consecutivas = 0
        resultado.drafts += 1
        resultado.drafts_alerted += int(rascunho.similarity_alert)
        desfecho = "alerta" if rascunho.similarity_alert else "ok"
        log_event(logger, "draft_artifact", alias, desfecho, None)
        return with_draft(atual, rascunho.draft_id)

    def _falha(
        self,
        alias: str,
        path: str,
        atual: ArtifactState,
        error: Exception,
        resultado: FolderTriageResult,
    ) -> ArtifactState:
        tipo = type(error).__name__
        indisponivel = isinstance(error, _INDISPONIBILIDADE)
        self.consecutivas = self.consecutivas + 1 if indisponivel else 0
        resultado.failures.append(ArtifactFailure(path, tipo))
        log_event(logger, "triage_artifact", alias, "falha", tipo)
        return with_failure(atual, tipo)

    def _triar(self, folder: Folder, path: str, kind: ArtifactKind, conteudo: str) -> Triage:
        restrita = _restrita(folder.license)
        tipo = _item_kind(kind)
        parecidos = select_similar(path, conteudo, self.deps.catalog.items(tipo)) if tipo else []
        entrada = TriageInput(
            alias=folder.alias.value,
            path=path,
            kind=kind,
            restricted_license=restrita,
            content=conteudo,
            library_index=self.indice,
            drafts_index=self._indice_rascunhos(kind, path, conteudo),
            similar=parecidos,
            criteria=self.prompts.criteria,
        )
        prompt = build_triage_prompt(entrada, self._nonce)
        resposta = self.chamar(
            ModelRole.TRIAGE, self.options.triage_model, self.prompts.triage, prompt, _TRIAGE_SCHEMA
        )
        triagem = _triage_de(resposta, self.prompts.fingerprint, self.now())
        ids = {d.draft_id for d in self.pendentes}
        validate_in_context(triagem, kind, restrita, self.deps.catalog.exists, ids.__contains__)
        return triagem

    def _indice_rascunhos(self, kind: ArtifactKind, path: str, conteudo: str) -> str:
        texto, truncou = drafts_index(self.pendentes, kind, path, conteudo)
        self.report.partial_dedupe = self.report.partial_dedupe or truncou
        return texto

    # --- rascunho (US2) --------------------------------------------------------------------

    def _rascunhar(self, folder: Folder, path: str, estado: ArtifactState, conteudo: str) -> Draft:
        triagem = estado.triage
        drafts = self.deps.drafts
        if triagem is None or drafts is None:  # garantido por _so_rascunho
            raise InvalidTriageError("rascunho sem triagem gap")
        alias = folder.alias.value
        restrita = _restrita(folder.license)
        alvo = triagem.merge_target
        existente = drafts.load(alvo.ref) if alvo and alvo.kind == "draft" else None
        acervo = self._item_do_acervo(alvo.ref) if alvo and alvo.kind == "library" else None
        entrada = DraftInput(
            alias=alias,
            path=path,
            kind=triagem.suggested_kind or estado.kind,
            source=triagem.ideas_summary if restrita and triagem.ideas_summary else conteudo,
            source_is_summary=restrita,
            merge_library=acervo,
            merge_draft=existente,
            regenerate=False,
        )
        custos: list[Decimal | None] = []
        proposta, modelo = self._proposta(entrada, custos)
        checks = [self._verificar(conteudo, proposta, custos)]
        if checks[0].flagged:
            proposta, modelo = self._proposta(replace(entrada, regenerate=True), custos)
            checks.append(self._verificar(conteudo, proposta, custos))
        conhecidos = [c for c in custos if c is not None]
        custo = sum(conhecidos, Decimal("0")) if len(conhecidos) == len(custos) else None
        origem = DraftOrigin(alias, path, estado.sha256)
        if existente is not None:
            draft_id = existente.draft_id
        else:
            draft_id = triagem.draft_id or draft_id_for(alias, path)
        with drafts.lock():
            anterior = existente or drafts.load(draft_id)
            rascunho = Draft(
                draft_id=draft_id,
                proposal=proposta,
                origins=anterior.origins if anterior else (origem,),
                checks=tuple(checks),
                merge_target=alvo or (anterior.merge_target if anterior else None),
                prompt_fingerprint=self.prompts.fingerprint,
                model=modelo,
                cost_usd=custo,
                updated_at=self.now(),
            ).with_origin(origem)
            drafts.save(rascunho)
            self.pendentes = drafts.list_pending()
        return rascunho

    def _item_do_acervo(self, ref: str) -> CatalogItem | None:
        tipo = ItemKind(ref.split("/", 1)[0])
        return next((i for i in self.deps.catalog.items(tipo) if i.ref == ref), None)

    def _proposta(
        self, entrada: DraftInput, custos: list[Decimal | None]
    ) -> tuple[DraftProposal, str]:
        resposta = self.chamar(
            ModelRole.DRAFT,
            self.options.draft_model,
            self.prompts.draft,
            build_draft_prompt(entrada, self._nonce),
            _DRAFT_SCHEMA,
        )
        custos.append(resposta.cost_usd)
        dados = resposta.payload
        try:
            proposta = DraftProposal(
                kind=ArtifactKind.from_str(str(dados["kind"])),
                name=str(dados["name"]),
                description=str(dados["description"]),
                body=str(dados["body"]),
            )
        except InvalidTriageError:
            raise
        except (PraxisForgeError, KeyError) as error:
            motivo = type(error).__name__
            raise InvalidTriageError(f"rascunho com forma inesperada: {motivo}") from error
        return proposta, resposta.model

    def _verificar(
        self, original: str, proposta: DraftProposal, custos: list[Decimal | None]
    ) -> SimilarityCheck:
        """Duas camadas (FR-017): esqueleto (código) e juiz (modelo barato, sem ferramentas)."""
        pontuacao = structural_score(skeleton_of(original), skeleton_of(proposta.body))
        resposta = self.chamar(
            ModelRole.JUDGE,
            self.options.triage_model,
            self.prompts.judge,
            build_judge_prompt(original, proposta.body, self._nonce),
            _JUDGE_SCHEMA,
        )
        custos.append(resposta.cost_usd)
        try:
            return SimilarityCheck(
                structural_score=round(pontuacao, 4),
                threshold=self.options.similarity_threshold,
                judge_is_derivative=bool(resposta.payload["is_derivative"]),
                judge_justification=str(resposta.payload["justification"]),
            )
        except (KeyError, ValueError) as error:
            motivo = type(error).__name__
            raise InvalidTriageError(f"parecer do juiz inválido: {motivo}") from error


def _triage_de(resposta: ModelReply, fingerprint: str, instante: datetime) -> Triage:
    """Resposta (já validada pelo schema) → veredito do domínio; forma inesperada é inválida."""
    dados = resposta.payload
    try:
        alvo = dados["merge_target"]
        sugerido = dados["suggested_kind"]
        return Triage(
            verdict=TriageVerdict.from_str(str(dados["verdict"])),
            justification=str(dados["justification"]),
            covered_by=tuple(str(ref) for ref in dados["covered_by"]),  # type: ignore[attr-defined]
            merge_target=(
                None if alvo is None else MergeTarget(str(alvo["kind"]), str(alvo["ref"]))  # type: ignore[index]
            ),
            suggested_kind=None if sugerido is None else ArtifactKind.from_str(str(sugerido)),
            ideas_summary=None if dados["ideas_summary"] is None else str(dados["ideas_summary"]),
            prompt_fingerprint=fingerprint,
            model=resposta.model,
            cost_usd=resposta.cost_usd,
            triaged_at=instante,
        )
    except InvalidTriageError:
        raise
    except (PraxisForgeError, KeyError, TypeError) as error:
        raise InvalidTriageError(
            f"resposta com forma inesperada: {type(error).__name__}"
        ) from error


def triage(
    deps: TriageDeps,
    alias: str | None,
    options: TriageOptions,
    *,
    now: Callable[[], datetime] | None = None,
) -> TriageReport:
    """
    Tria uma pasta (alias) ou todas as inventariadas, exceto `ignore` (FR-001 a FR-004).

    Antes da 1ª chamada: verifica o modelo (FR-037) e carrega os prompts (FR-021). O estado é
    gravado após cada artefato (FR-024); a retomada é rodar de novo (FR-029).

    :param deps: portas compostas.
    :param alias: alias específico, ou None para todas as pastas.
    :param options: opções validadas.
    :param now: relógio (padrão: agora em America/Sao_Paulo).
    :return: relatório da execução.
    :rtype: TriageReport
    :raises FolderNotFoundError: alias não registrado.
    :raises CurationNotInventoriedError: alias sem inventário.
    :raises CurationLockedError: outra execução no mesmo alias.
    :raises LanguageModelNotInstalledError: CLI ausente.
    :raises LanguageModelUntestedVersionError: CLI fora da faixa testada (falha fechada).
    :raises PromptSetError: prompt ausente ou vazio.
    """
    relogio = now or (lambda: datetime.now(_TZ))
    registry = deps.repository.load()
    pastas = [registry.get(alias)] if alias is not None else registry.list()
    deps.model.check_ready()
    execucao = _Execucao(deps, options, deps.prompts.load(), relogio)
    for folder in sorted(pastas, key=lambda f: f.alias.value):
        nome = folder.alias.value
        if alias is None and folder.status is CurationStatus.IGNORE:
            execucao.report.skipped.append(nome)
            continue
        if alias is not None:
            execucao.report.folders.append(execucao.pasta(folder))
            continue
        try:
            execucao.report.folders.append(execucao.pasta(folder))
        except PraxisForgeError as error:
            log_event(logger, "triage_folder", nome, "falha", type(error).__name__)
            execucao.report.failures.append(
                ItemFailure(alias=nome, error_type=type(error).__name__, message=str(error))
            )
    execucao.report.calls = execucao.budget.calls
    execucao.report.cost = execucao.budget.cost
    execucao.report.cost_measurable = execucao.budget.cost_measurable
    return execucao.report
