# -*- coding: utf-8 -*-
"""
NOME: json_curation_store.py
TITULO: Adapter CurationStore — manifesto e estado em JSON por alias, com lock e gravação atômica
DATA: 25/09/2026 15:14
MODIFICADO: 25/09/2026 14:56
VERSÃO: 0.1.0
DEPEND: fcntl (Linux), praxisforge.application.ports
HISTÓRICO:
    - 25/09/2026 15:14: criação (T018, feature 010) — faz test_json_curation_store.py passar
STATUS: DEV
"""

import fcntl
import json
import logging
import os
import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from praxisforge.application.ports import ContractValidator, CurationStore
from praxisforge.domain.curation_artifact import ArtifactKind, Manifest, Stage
from praxisforge.domain.curation_state import ArtifactState, CurationState
from praxisforge.domain.errors import (
    CurationLockedError,
    CurationStateCorruptError,
    CurationStorageError,
    PraxisForgeError,
)

logger = logging.getLogger(__name__)

_MANIFEST = "manifest.json"
_STATE = "state.json"
_LOCK = ".lock"


def manifest_document(manifest: Manifest) -> dict[str, Any]:
    """Serializa o manifesto (sem data — determinístico)."""
    return {
        "schema_version": "1",
        "alias": manifest.alias,
        "conventions_version": manifest.conventions_version,
        "artifacts": [
            {
                "path": a.path,
                "kind": a.kind.value,
                "size": a.size,
                "sha256": a.sha256,
                "files": a.files,
            }
            for a in manifest.artifacts
        ],
        "excluded": [
            {"path": e.path, "reason": e.reason.value, "is_dir": e.is_dir}
            for e in manifest.excluded
        ],
    }


def state_document(state: CurationState) -> dict[str, Any]:
    """Serializa o estado da curadoria."""
    return {
        "schema_version": "1",
        "alias": state.alias,
        "conventions_version": state.conventions_version,
        "updated_at": state.updated_at.isoformat(timespec="seconds"),
        "artifacts": {
            path: {
                "kind": s.kind.value,
                "sha256": s.sha256,
                "stage": s.stage.value,
                "verdict": s.verdict,
                "last_error": s.last_error,
                "attempts": s.attempts,
            }
            for path, s in state.artifacts.items()
        },
    }


def _dump(documento: dict[str, Any]) -> str:
    return json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


class JsonCurationStore(CurationStore):
    """
    Guarda `<base>/<alias>/{manifest.json,state.json}` fora do repositório (FR-009).

    :param base_dir: diretório `curation/` ao lado do registro.
    :type base_dir: Path
    :param validator: validador de contratos JSON Schema.
    :type validator: ContractValidator
    """

    def __init__(self, base_dir: Path, validator: ContractValidator) -> None:
        self._base = base_dir
        self._validator = validator

    def _dir(self, alias: str) -> Path:
        return self._base / alias

    def lock(self, alias: str) -> AbstractContextManager[None]:
        """Ver CurationStore.lock (flock; liberado pelo kernel se o processo morrer)."""
        return self._lock(alias)

    @contextmanager
    def _lock(self, alias: str) -> Iterator[None]:
        try:
            self._dir(alias).mkdir(parents=True, exist_ok=True)
            descritor = os.open(self._dir(alias) / _LOCK, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError as error:
            raise CurationStorageError(alias, type(error).__name__) from error
        try:
            try:
                fcntl.flock(descritor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise CurationLockedError(alias) from error
            try:
                yield
            finally:
                fcntl.flock(descritor, fcntl.LOCK_UN)
        finally:
            os.close(descritor)

    def load_state(self, alias: str) -> CurationState | None:
        """Ver CurationStore.load_state."""
        arquivo = self._dir(alias) / _STATE
        if not arquivo.exists():
            return None
        try:
            documento = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CurationStateCorruptError(alias, type(error).__name__) from error
        if not isinstance(documento, dict):
            raise CurationStateCorruptError(alias, "documento não é um objeto")
        try:
            self._validator.validate(documento, "curation-state-schema-v1")
            if documento["alias"] != alias:
                raise CurationStateCorruptError(alias, f"pertence a '{documento['alias']}'")
            return CurationState(
                alias=documento["alias"],
                conventions_version=documento["conventions_version"],
                updated_at=datetime.fromisoformat(documento["updated_at"]),
                artifacts={
                    path: ArtifactState(
                        kind=ArtifactKind.from_str(s["kind"]),
                        sha256=s["sha256"],
                        stage=Stage.from_str(s["stage"]),
                        verdict=s["verdict"],
                        last_error=s["last_error"],
                        attempts=s["attempts"],
                    )
                    for path, s in documento["artifacts"].items()
                },
            )
        except CurationStateCorruptError:
            raise
        except (PraxisForgeError, ValueError) as error:
            raise CurationStateCorruptError(alias, str(error)) from error

    def save(self, manifest: Manifest, state: CurationState) -> None:
        """Ver CurationStore.save (valida antes; temp + os.replace)."""
        alias = state.alias
        documentos = {
            _MANIFEST: (manifest_document(manifest), "curation-manifest-schema-v1"),
            _STATE: (state_document(state), "curation-state-schema-v1"),
        }
        try:
            for documento, schema in documentos.values():
                self._validator.validate(documento, schema)
        except PraxisForgeError as error:
            raise CurationStorageError(alias, f"documento fora do contrato: {error}") from error
        destino = self._dir(alias)
        try:
            destino.mkdir(parents=True, exist_ok=True)
            # manifesto antes do estado: o estado só aponta para um manifesto já gravado
            for nome, (documento, _) in documentos.items():
                self._gravar(destino / nome, _dump(documento))
        except OSError as error:
            logger.error("falha ao gravar a curadoria de %s", alias, exc_info=True)
            raise CurationStorageError(alias, type(error).__name__) from error

    @staticmethod
    def _gravar(alvo: Path, conteudo: str) -> None:
        descritor, temporario = tempfile.mkstemp(dir=alvo.parent, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(descritor, "w", encoding="utf-8") as saida:
                saida.write(conteudo)
            os.replace(temporario, alvo)
        except OSError:
            Path(temporario).unlink(missing_ok=True)
            raise
