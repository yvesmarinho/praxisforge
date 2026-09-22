# -*- coding: utf-8 -*-
"""
NOME: errors.py
TITULO: Reexportação de exceções semânticas para a Presentation (sem importar Domain diretamente)
DATA: 22/09/2026 10:05
MODIFICADO: 22/09/2026 10:09
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
STATUS: DEV
"""

from praxisforge.domain.errors import (
    ContractValidationError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathNotConfiguredError,
    FolderPathUnreadableError,
    PraxisForgeError,
    RegistryUnavailableError,
)

__all__ = [
    "ContractValidationError",
    "FolderNotFoundError",
    "FolderPathInvalidError",
    "FolderPathNotConfiguredError",
    "FolderPathUnreadableError",
    "PraxisForgeError",
    "RegistryUnavailableError",
]
