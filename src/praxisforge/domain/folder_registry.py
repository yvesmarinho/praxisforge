# -*- coding: utf-8 -*-
"""
NOME: folder_registry.py
TITULO: Agregado FolderRegistry — coleção de pastas registradas, com invariantes
DATA: 22/09/2026 09:45
MODIFICADO: 25/09/2026 09:52
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.folder, praxisforge.domain.curation_status, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 09:45: criação (T021) — faz tests/unit/domain/test_folder_registry.py passar
    - 23/09/2026 12:07: update() aceita last_curated_commit (T013, feature 004)
    - 23/09/2026 16:55: path único e sem aninhamento (T013, feature 005)
    - 24/09/2026 09:37: componentes do caminho em cache (checagem por pares ficava cara em lote)
    - 25/09/2026 09:52: folders update --description
STATUS: DEV
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from functools import lru_cache

from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    AliasAlreadyRegisteredError,
    FolderNotFoundError,
    NestedFolderPathError,
    PathAlreadyRegisteredError,
    UnsupportedSchemaVersionError,
)
from praxisforge.domain.folder import Folder

SUPPORTED_SCHEMA_VERSIONS = ("2",)


@dataclass(frozen=True)
class FolderRegistry:
    """
    Agregado que garante aliases únicos, caminhos únicos e sem aninhamento, e a versão do contrato.

    Caminhos são comparados sem diferenciar maiúsculas/minúsculas (feature 005, FR-003).

    :param schema_version: versão do contrato (só `"2"` é suportada; v1 só via migração).
    :type schema_version: str
    :param folders: mapa alias (str) → Folder.
    :type folders: dict[str, Folder]
    :raises UnsupportedSchemaVersionError: `schema_version` fora do suportado.
    :raises PathAlreadyRegisteredError: duas pastas com o mesmo caminho.
    :raises NestedFolderPathError: uma pasta dentro de outra.
    """

    schema_version: str
    folders: dict[str, Folder]

    def __post_init__(self) -> None:
        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise UnsupportedSchemaVersionError(
                found=self.schema_version, supported=SUPPORTED_SCHEMA_VERSIONS
            )
        vistas: list[Folder] = []
        for alias in sorted(self.folders):
            folder = self.folders[alias]
            _verificar_conflito(folder.path, vistas)
            vistas.append(folder)

    def find_by_path(self, path: str) -> Folder | None:
        """
        Procura a pasta registrada com o caminho informado (sem diferenciar maiúsculas).

        :param path: caminho absoluto.
        :type path: str
        :return: a pasta, ou None se nenhuma usa esse caminho.
        :rtype: Folder | None
        """
        chave = path.casefold()
        for folder in self.folders.values():
            if folder.path.casefold() == chave:
                return folder
        return None

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
        :raises PathAlreadyRegisteredError: caminho já usado por outra pasta.
        :raises NestedFolderPathError: caminho dentro de (ou contendo) outra pasta.
        """
        alias = str(folder.alias)
        existing = self.folders.get(alias)
        if existing is not None:
            if existing == folder:
                return self
            raise AliasAlreadyRegisteredError(alias)
        _verificar_conflito(folder.path, list(self.folders.values()))
        new_folders = {**self.folders, alias: folder}
        return replace(self, folders=new_folders)

    def update(
        self,
        alias: str,
        status: CurationStatus | None = None,
        last_scanned: datetime | None = None,
        license: str | None = None,  # noqa: A002 - nome do domínio
        last_curated_commit: str | None = None,
        path: str | None = None,
        description: str | None = None,
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
        :param last_curated_commit: novo hash da versão curada, se informado.
        :type last_curated_commit: str | None
        :param path: novo caminho absoluto, se informado (revalida unicidade/aninhamento).
        :type path: str | None
        :param description: nova descrição, se informada (1 a 500 caracteres).
        :type description: str | None
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
            last_curated_commit=(
                last_curated_commit
                if last_curated_commit is not None
                else current.last_curated_commit
            ),
            path=path if path is not None else current.path,
            description=description if description is not None else current.description,
        )
        if path is not None:
            outras = [f for key, f in self.folders.items() if key != alias]
            _verificar_conflito(updated.path, outras)
        new_folders = {**self.folders, alias: updated}
        return replace(self, folders=new_folders)

    def list(self) -> list[Folder]:
        """
        Lista todas as pastas ordenadas por alias.

        :return: lista ordenada de pastas.
        :rtype: list[Folder]
        """
        return [self.folders[key] for key in sorted(self.folders)]


def _verificar_conflito(path: str, outras: list[Folder]) -> None:
    """Aplica `ensure_path_available` contra as pastas informadas (sem a própria)."""
    ensure_path_available(path, {str(outra.alias): outra.path for outra in outras})


def ensure_path_available(path: str, ocupados: Mapping[str, str]) -> None:
    """
    Garante que `path` não repete nem aninha com nenhum caminho já ocupado.

    Comparação por componentes e sem diferenciar maiúsculas/minúsculas (FR-003).

    :param path: caminho candidato.
    :type path: str
    :param ocupados: mapa alias → caminho já registrado.
    :type ocupados: Mapping[str, str]
    :raises PathAlreadyRegisteredError: mesmo caminho.
    :raises NestedFolderPathError: um caminho é ancestral do outro.

    :Example:

    >>> ensure_path_available("/srv/b", {"pasta_a": "/srv/a"})
    >>> ensure_path_available("/srv/forks2", {"pasta_a": "/srv/forks"})
    """
    candidato = _componentes(path)
    for alias, outro in ocupados.items():
        existente = _componentes(outro)
        if candidato == existente:
            raise PathAlreadyRegisteredError(alias)
        menor = min(len(candidato), len(existente))
        if candidato[:menor] == existente[:menor]:
            raise NestedFolderPathError(alias)


@lru_cache(maxsize=4096)
def _componentes(path: str) -> tuple[str, ...]:
    """Componentes do caminho em casefold; "/" vira tupla vazia (ancestral de tudo)."""
    return tuple(parte for parte in path.casefold().split("/") if parte)
