# -*- coding: utf-8 -*-
"""
NOME: yaml_folder_registry.py
TITULO: Adapter YAML do FolderRegistryRepository — escrita atômica e determinística
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:07
VERSÃO: 0.1.0
DEPEND: pyyaml, praxisforge.application.ports, praxisforge.domain
HISTÓRICO:
    - 22/09/2026 09:45: criação (T034) — faz tests/integration/test_yaml_folder_registry.py passar
    - 23/09/2026 12:07: (de)serializa last_curated_commit, omitido quando None (T014, feature 004)
STATUS: DEV
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import cast

import yaml

from praxisforge.application.ports import ContractValidator, FolderRegistryRepository
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import RegistryFileNotFoundError, RegistryUnavailableError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry
from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader


class YamlFolderRegistryRepository(FolderRegistryRepository):
    """
    Adapter que persiste o FolderRegistry em `folders.yaml` (escrita atômica).

    :param path: caminho do arquivo do registro.
    :type path: Path
    :param validator: validador de contrato usado ao carregar (schema `folders-schema-v1`).
    :type validator: ContractValidator
    """

    def __init__(self, path: Path, validator: ContractValidator) -> None:
        self._path = path
        self._validator = validator

    def exists(self) -> bool:
        """Ver FolderRegistryRepository.exists."""
        return self._path.exists()

    def load_raw(self) -> dict[str, object]:
        """Ver FolderRegistryRepository.load_raw."""
        if not self._path.exists():
            raise RegistryFileNotFoundError
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                # NoTimestampSafeLoader só remove o resolvedor de timestamp do
                # SafeLoader; não adiciona construtores !!python/object (research.md D16)
                documento = yaml.load(handle, Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
        except PermissionError as error:
            raise RegistryUnavailableError("sem permissão de leitura do registro") from error
        except yaml.YAMLError as error:
            raise RegistryUnavailableError(f"registro corrompido: {error}") from error
        except OSError as error:
            raise RegistryUnavailableError(f"registro ilegível: {error}") from error
        if not isinstance(documento, dict):
            raise RegistryUnavailableError("registro corrompido: documento raiz não é um mapa")
        return documento

    def load(self) -> FolderRegistry:
        """Ver FolderRegistryRepository.load."""
        documento = self.load_raw()
        self._validator.validate(documento, schema_name="folders-schema-v1")
        folders_raw = cast(dict[str, dict[str, object]], documento.get("folders") or {})
        folders: dict[str, Folder] = {}
        for alias_str, entry in folders_raw.items():
            last_scanned_raw = entry.get("last_scanned")
            last_scanned = (
                datetime.fromisoformat(str(last_scanned_raw)) if last_scanned_raw else None
            )
            folders[alias_str] = Folder(
                alias=Alias(alias_str),
                description=str(entry["description"]),
                content_type=str(entry["content_type"]),
                license=str(entry["license"]),
                last_scanned=last_scanned,
                status=CurationStatus.from_str(str(entry["status"])),
                last_curated_commit=(
                    str(entry["last_curated_commit"]) if "last_curated_commit" in entry else None
                ),
            )
        return FolderRegistry(
            schema_version=str(documento.get("schema_version", "")), folders=folders
        )

    def save(self, registry: FolderRegistry) -> None:
        """Ver FolderRegistryRepository.save."""
        documento: dict[str, object] = {
            "schema_version": registry.schema_version,
            "folders": {folder.alias.value: _serializar(folder) for folder in registry.list()},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=self._path.parent, prefix=f".{self._path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                yaml.safe_dump(
                    documento,
                    handle,
                    sort_keys=True,
                    allow_unicode=True,
                    default_flow_style=False,
                )
            os.replace(tmp_name, self._path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


def _serializar(folder: Folder) -> dict[str, object]:
    """
    Converte uma Folder no mapa YAML; `last_curated_commit` só aparece quando presente.

    :param folder: pasta a serializar.
    :type folder: Folder
    :return: mapa pronto para o YAML (chave opcional omitida quando None — FR-012).
    :rtype: dict[str, object]
    """
    entry: dict[str, object] = {
        "description": folder.description,
        "content_type": folder.content_type,
        "license": folder.license,
        "last_scanned": folder.last_scanned.isoformat() if folder.last_scanned else None,
        "status": folder.status.value,
    }
    if folder.last_curated_commit is not None:
        entry["last_curated_commit"] = folder.last_curated_commit
    return entry
