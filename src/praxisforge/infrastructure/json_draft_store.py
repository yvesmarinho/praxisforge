# -*- coding: utf-8 -*-
"""
NOME: json_draft_store.py
TITULO: Adapter DraftStore — rascunhos em curation/_drafts/<id>.json, com lock e gravação atômica
DATA: 28/09/2026 16:17
MODIFICADO: 28/09/2026 16:17
VERSÃO: 0.1.0
DEPEND: fcntl (Linux), praxisforge.application.ports
HISTÓRICO:
    - 28/09/2026 16:17: criação (T039, feature 011) — faz test_json_draft_store.py passar
STATUS: DEV
"""

import fcntl
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from praxisforge.application.ports import ContractValidator, DraftStore
from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.curation_draft import Draft, DraftOrigin, DraftProposal
from praxisforge.domain.curation_triage import DRAFT_ID, MergeTarget
from praxisforge.domain.errors import (
    CurationLockedError,
    CurationPathUnsafeError,
    CurationStorageError,
    DraftStoreCorruptError,
    PraxisForgeError,
)
from praxisforge.domain.structure_similarity import SimilarityCheck

_AREA = "_drafts"
_LOCK = ".lock"
_SCHEMA = "curation-draft-schema-v1"


def draft_document(draft: Draft) -> dict[str, Any]:
    """Serializa o rascunho no contrato `curation-draft-schema-v1`."""
    alvo = draft.merge_target
    return {
        "schema_version": "1",
        "draft_id": draft.draft_id,
        "proposal": {
            "kind": draft.proposal.kind.value,
            "name": draft.proposal.name,
            "description": draft.proposal.description,
            "body": draft.proposal.body,
        },
        "origins": [{"alias": o.alias, "path": o.path, "sha256": o.sha256} for o in draft.origins],
        "checks": [
            {
                "structural_score": c.structural_score,
                "threshold": c.threshold,
                "judge_is_derivative": c.judge_is_derivative,
                "judge_justification": c.judge_justification,
                "flagged": c.flagged,
            }
            for c in draft.checks
        ],
        "similarity_alert": draft.similarity_alert,
        "merge_target": None if alvo is None else {"kind": alvo.kind, "ref": alvo.ref},
        "prompt_fingerprint": draft.prompt_fingerprint,
        "model": draft.model,
        "cost_usd": None if draft.cost_usd is None else float(draft.cost_usd),
        "updated_at": draft.updated_at.isoformat(timespec="seconds"),
    }


def _draft_de(documento: dict[str, Any]) -> Draft:
    proposta = documento["proposal"]
    alvo = documento["merge_target"]
    return Draft(
        draft_id=documento["draft_id"],
        proposal=DraftProposal(
            kind=ArtifactKind.from_str(proposta["kind"]),
            name=proposta["name"],
            description=proposta["description"],
            body=proposta["body"],
        ),
        origins=tuple(
            DraftOrigin(o["alias"], o["path"], o["sha256"]) for o in documento["origins"]
        ),
        checks=tuple(
            SimilarityCheck(
                c["structural_score"],
                c["threshold"],
                c["judge_is_derivative"],
                c["judge_justification"],
            )
            for c in documento["checks"]
        ),
        merge_target=None if alvo is None else MergeTarget(alvo["kind"], alvo["ref"]),
        prompt_fingerprint=documento["prompt_fingerprint"],
        model=documento["model"],
        cost_usd=None if documento["cost_usd"] is None else Decimal(str(documento["cost_usd"])),
        updated_at=datetime.fromisoformat(documento["updated_at"]),
    )


class JsonDraftStore(DraftStore):
    """
    Guarda `<base>/_drafts/<draft_id>.json` fora do repositório (R8, FR-043, FR-044).

    :param base_dir: diretório `curation/` ao lado do registro.
    :type base_dir: Path
    :param validator: validador de contratos JSON Schema.
    :type validator: ContractValidator
    """

    def __init__(self, base_dir: Path, validator: ContractValidator) -> None:
        self._base = base_dir
        self._area = base_dir / _AREA
        self._validator = validator

    def _check_safe(self, *caminhos: Path) -> None:
        for caminho in (self._base, self._area, *caminhos):
            if caminho.is_symlink():
                raise CurationPathUnsafeError(str(caminho.relative_to(self._base.parent)))

    def _ensure(self) -> None:
        self._check_safe()
        for diretorio in (self._base, self._area):
            diretorio.mkdir(mode=0o700, parents=True, exist_ok=True)
            diretorio.chmod(0o700)

    def lock(self) -> AbstractContextManager[None]:
        """Ver DraftStore.lock (flock; liberado pelo kernel se o processo morrer)."""
        return self._lock()

    @contextmanager
    def _lock(self) -> Iterator[None]:
        try:
            self._ensure()
            descritor = os.open(self._area / _LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        except OSError as error:
            raise CurationStorageError(_AREA, type(error).__name__) from error
        try:
            try:
                fcntl.flock(descritor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise CurationLockedError(_AREA) from error
            try:
                yield
            finally:
                fcntl.flock(descritor, fcntl.LOCK_UN)
        finally:
            os.close(descritor)

    def _ler(self, arquivo: Path) -> Draft:
        draft_id = arquivo.stem
        if not DRAFT_ID.match(draft_id):
            raise DraftStoreCorruptError(draft_id, "nome de arquivo fora do formato de id")
        self._check_safe(arquivo)
        try:
            documento = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DraftStoreCorruptError(draft_id, type(error).__name__) from error
        if not isinstance(documento, dict):
            raise DraftStoreCorruptError(draft_id, "documento não é um objeto")
        try:
            self._validator.validate(documento, _SCHEMA)
            if documento["draft_id"] != draft_id:
                raise DraftStoreCorruptError(draft_id, "id do documento difere do arquivo")
            return _draft_de(documento)
        except DraftStoreCorruptError:
            raise
        except (PraxisForgeError, ValueError, KeyError) as error:
            raise DraftStoreCorruptError(draft_id, str(error)[:200]) from error

    def list_pending(self) -> list[Draft]:
        """Ver DraftStore.list_pending."""
        self._check_safe()
        if not self._area.is_dir():
            return []
        return [self._ler(a) for a in sorted(self._area.glob("*.json"))]

    def load(self, draft_id: str) -> Draft | None:
        """Ver DraftStore.load."""
        if not DRAFT_ID.match(draft_id):
            return None
        arquivo = self._area / f"{draft_id}.json"
        self._check_safe(arquivo)
        return self._ler(arquivo) if arquivo.exists() else None

    def save(self, draft: Draft) -> None:
        """Ver DraftStore.save."""
        documento = draft_document(draft)
        try:
            self._validator.validate(documento, _SCHEMA)
        except PraxisForgeError as error:
            raise CurationStorageError(_AREA, f"rascunho fora do contrato: {error}") from error
        alvo = self._area / f"{draft.draft_id}.json"
        self._check_safe(alvo)
        try:
            self._ensure()
            descritor, temporario = tempfile.mkstemp(dir=self._area, prefix=".tmp-", suffix=".json")
            try:
                os.fchmod(descritor, 0o600)
                with os.fdopen(descritor, "w", encoding="utf-8") as saida:
                    saida.write(json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=True))
                    saida.write("\n")
                os.replace(temporario, alvo)
            except OSError:
                Path(temporario).unlink(missing_ok=True)
                raise
        except OSError as error:
            raise CurationStorageError(_AREA, type(error).__name__) from error

    def alerts_for(self, alias: str) -> int:
        """Ver DraftStore.alerts_for."""
        return sum(
            1
            for d in self.list_pending()
            if d.similarity_alert and any(o.alias == alias for o in d.origins)
        )
