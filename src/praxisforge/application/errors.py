# -*- coding: utf-8 -*-
"""
NOME: errors.py
TITULO: Reexportação de exceções semânticas para a Presentation (sem importar Domain diretamente)
DATA: 22/09/2026 10:05
MODIFICADO: 25/09/2026 13:00
VERSÃO: 0.1.0
DEPEND: praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 10:05: criação — corrige violação de camada revelada por
      tests/architecture/test_layer_rules.py (presentation/cli.py importava
      praxisforge.domain.errors diretamente)
    - 22/09/2026 10:20: adiciona os erros de resolução de caminho (US2), para a
      CLI distinguir código de saída 1 (validação/negócio) de 3 (ambiente)
    - 22/09/2026 10:45: adiciona ContractValidationError e RegistryUnavailableError (US3),
      usados por `sources validate` na CLI
    - 22/09/2026 18:20: adiciona InvalidRootPathError (feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:07: reexporta ContentInspectionError (T011, feature 004)
    - 24/09/2026 10:52: reexporta exceções da política de extração (T009, feature 006)
    - 24/09/2026 14:31: reexporta exceções da realocação do registro (T006, feature 007)
    - 24/09/2026 16:54: reexporta exceções da biblioteca de skills (T008, feature 008)
    - 25/09/2026 09:57: reexporta ProjectRootNotFoundError
    - 25/09/2026 13:00: reexporta exceções do acervo library/ (T009, feature 009)
STATUS: DEV
"""

from praxisforge.domain.errors import (
    CatalogWriteError,
    ContentInspectionError,
    ContractValidationError,
    ExtractPolicyExceedsLicenseError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathUnreadableError,
    ForeignSkillDestinationError,
    GlobalTargetRemovedError,
    IncompleteAttributionError,
    IndexWriteError,
    InvalidLibraryItemError,
    InvalidRootPathError,
    InvalidSkillError,
    LibraryItemNotFoundError,
    LibraryNotFoundError,
    NestedFolderPathError,
    NothingToRelocateError,
    NotPublishableKindError,
    PathAlreadyRegisteredError,
    PraxisForgeError,
    ProjectRootNotFoundError,
    RegistryAlreadyExistsError,
    RegistryFileNotFoundError,
    RegistryMigrationRequiredError,
    RegistryRelocationError,
    RegistryUnavailableError,
    SkillNotFoundError,
    SkillPublicationError,
    SkillVersionNotBumpedError,
    SourceSchemaMigrationRequiredError,
    UnknownItemKindError,
)

__all__ = [
    "CatalogWriteError",
    "ContentInspectionError",
    "ContractValidationError",
    "ExtractPolicyExceedsLicenseError",
    "FolderNotFoundError",
    "FolderPathInvalidError",
    "FolderPathUnreadableError",
    "ForeignSkillDestinationError",
    "GlobalTargetRemovedError",
    "IncompleteAttributionError",
    "IndexWriteError",
    "InvalidLibraryItemError",
    "InvalidRootPathError",
    "InvalidSkillError",
    "LibraryItemNotFoundError",
    "LibraryNotFoundError",
    "NestedFolderPathError",
    "NotPublishableKindError",
    "NothingToRelocateError",
    "PathAlreadyRegisteredError",
    "PraxisForgeError",
    "ProjectRootNotFoundError",
    "RegistryAlreadyExistsError",
    "RegistryFileNotFoundError",
    "RegistryMigrationRequiredError",
    "RegistryRelocationError",
    "RegistryUnavailableError",
    "SkillNotFoundError",
    "SkillPublicationError",
    "SkillVersionNotBumpedError",
    "SourceSchemaMigrationRequiredError",
    "UnknownItemKindError",
]
