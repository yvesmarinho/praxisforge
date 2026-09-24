# -*- coding: utf-8 -*-
"""
NOME: test_env_legacy_path_source.py
TITULO: Testes de integração — EnvLegacyPathSource (variáveis antigas, só para a migração)
DATA: 23/09/2026 16:48
MODIFICADO: 23/09/2026 16:48
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.env_legacy_path_source
HISTÓRICO:
    - 23/09/2026 16:48: criação (T008, feature 005-caminho-absoluto-registro)
STATUS: DEV
"""

from praxisforge.infrastructure.env_legacy_path_source import EnvLegacyPathSource


def test_lookup_le_variavel_do_alias(env_folder: object) -> None:
    """lookup devolve o valor de PRAXISFORGE_FOLDER_<ALIAS>."""
    env_folder.set("github_forks", "/srv/forks")  # type: ignore[attr-defined]
    assert EnvLegacyPathSource().lookup("github_forks") == "/srv/forks"


def test_lookup_ausente_ou_vazia_devolve_none(env_folder: object) -> None:
    """Variável ausente ou vazia → None (a migração tenta a raiz em seguida)."""
    env_folder.unset("github_forks")  # type: ignore[attr-defined]
    assert EnvLegacyPathSource().lookup("github_forks") is None
    env_folder.set("github_forks", "")  # type: ignore[attr-defined]
    assert EnvLegacyPathSource().lookup("github_forks") is None
