# -*- coding: utf-8 -*-
"""
NOME: folder_registry.py
TITULO: Agregado FolderRegistry — coleção de pastas registradas, com invariantes
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:50
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.folder, praxisforge.domain.curation_status, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T021) — faz tests/unit/domain/test_folder_registry.py passar
STATUS: DEV
"""

from dataclasses import dataclass, replace
from datetime import datetime

from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    AliasAlreadyRegisteredError,
    FolderNotFoundError,
    UnsupportedSchemaVersionError,
)
from praxisforge.domain.folder import Folder

SUPPORTED_SCHEMA_VERSIONS = ("1",)


@dataclass(frozen=True)
class FolderRegistry:
    """
    Agregado que garante aliases únicos e a versão do contrato do registro.

    :param schema_version: versão do contrato (só `"1"` é suportada).
    :type schema_version: str
    :param folders: mapa alias (str) → Folder.
    :type folders: dict[str, Folder]
    :raises UnsupportedSchemaVersionError: `schema_version` fora do suportado.
    """

    schema_version: str
    folders: dict[str, Folder]

    def __post_init__(self) -> None:
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise UnsupportedSchemaVersionError(
                found=self.schema_version, supported=SUPPORTED_SCHEMA_VERSIONS
            )

    def get(self, alias: str) -> Folder:
        """
        Consulta uma pasta pelo alias.

        :param alias: alias a consultar.
        :type alias: str
        :return: a pasta registrada.
        :rtype: Folder
        :raises FolderNotFoundError: alias não registrado.
        """
        try:
            return self.folders[alias]
        except KeyError as error:
            raise FolderNotFoundError(alias) from error

    def add(self, folder: Folder) -> "FolderRegistry":
        """
        Registra uma nova pasta (idempotente se dados idênticos).

        :param folder: pasta a registrar.
        :type folder: Folder
        :return: novo agregado com a pasta adicionada.
        :rtype: FolderRegistry
        :raises AliasAlreadyRegisteredError: alias já existe com dados diferentes.
        """
        alias = str(folder.alias)
        existing = self.folders.get(alias)
        if existing is not None:
            if existing == folder:
                return self
            raise AliasAlreadyRegisteredError(alias)
        new_folders = {**self.folders, alias: folder}
        return replace(self, folders=new_folders)

    def update(
        self,
        alias: str,
        status: CurationStatus | None = None,
        last_scanned: datetime | None = None,
        license: str | None = None,  # noqa: A002 - nome do domínio
    ) -> "FolderRegistry":
        """
        Atualiza campos informados de uma pasta, atomicamente.

        Só os campos explicitamente informados (não `None` neste método) são
        alterados; os demais mantêm o valor atual. A operação é atômica: se a
        combinação resultante violar uma invariante de `Folder`, nada é alterado.

        :param alias: alias da pasta a atualizar.
        :type alias: str
        :param status: novo status, se informado.
        :type status: CurationStatus | None
        :param last_scanned: nova data de varredura, se informada.
        :type last_scanned: datetime | None
        :param license: nova licença, se informada.
        :type license: str | None
        :return: novo agregado com a pasta atualizada.
        :rtype: FolderRegistry
        :raises FolderNotFoundError: alias não registrado.
        """
        current = self.get(alias)
        updated = replace(
            current,
            status=status if status is not None else current.status,
            last_scanned=last_scanned if last_scanned is not None else current.last_scanned,
            license=license if license is not None else current.license,
        )
        new_folders = {**self.folders, alias: updated}
        return replace(self, folders=new_folders)

    def list(self) -> list[Folder]:
        """
        Lista todas as pastas ordenadas por alias.

        :return: lista ordenada de pastas.
        :rtype: list[Folder]
        """
        return [self.folders[key] for key in sorted(self.folders)]
