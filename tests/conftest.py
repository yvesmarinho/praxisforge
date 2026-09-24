# -*- coding: utf-8 -*-
"""
NOME: conftest.py
TITULO: Fixtures compartilhadas entre tests/unit, tests/integration, tests/contract
DATA: 22/09/2026 09:45
MODIFICADO: 24/09/2026 14:31
VERSÃO: 0.1.0
DEPEND: pytest
HISTÓRICO:
    - 22/09/2026 09:45: criação (T002) — tmp_registry_path, env_folder, valid_folder_doc, fixed_now
    - 24/09/2026 14:31: fixture autouse isolando o local do registro do usuário (T008, feature 007)
STATUS: DEV
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture(autouse=True)
def _isolar_config_do_usuario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Nenhum teste lê ou grava o registro real do usuário (SC-001, feature 007).

    Aponta `XDG_CONFIG_HOME` para um diretório temporário e remove `PRAXISFORGE_REGISTRY`.

    :param tmp_path: diretório temporário isolado por teste (pytest).
    :type tmp_path: Path
    :param monkeypatch: fixture de ajuste de ambiente (pytest).
    :type monkeypatch: pytest.MonkeyPatch
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("PRAXISFORGE_REGISTRY", raising=False)


@pytest.fixture
def tmp_registry_path(tmp_path: Path) -> Path:
    """
    Caminho de um arquivo de registro YAML dentro de um diretório temporário.

    O arquivo não é criado por esta fixture; cabe ao teste decidir se o
    registro já existe ou se deve ser criado pela operação testada.

    :param tmp_path: diretório temporário isolado por teste (pytest).
    :type tmp_path: Path
    :return: caminho para `folders.yaml` dentro de `tmp_path`.
    :rtype: Path
    """
    return tmp_path / "folders.yaml"


@pytest.fixture
def env_folder(monkeypatch: pytest.MonkeyPatch) -> object:
    """
    Fábrica para definir/limpar variáveis `PRAXISFORGE_FOLDER_<ALIAS>`.

    :param monkeypatch: fixture padrão do pytest para alterar o ambiente.
    :type monkeypatch: pytest.MonkeyPatch
    :return: função `set(alias, value)` / `unset(alias)`.
    :rtype: object

    :Example:

    >>> def test_x(env_folder, tmp_path):
    ...     env_folder.set("github_forks", str(tmp_path))
    """

    class _EnvFolder:
        @staticmethod
        def set(alias: str, value: str) -> None:
            monkeypatch.setenv(f"PRAXISFORGE_FOLDER_{alias.upper()}", value)

        @staticmethod
        def unset(alias: str) -> None:
            monkeypatch.delenv(f"PRAXISFORGE_FOLDER_{alias.upper()}", raising=False)

    return _EnvFolder()


@pytest.fixture
def valid_folder_doc() -> dict[str, object]:
    """
    Documento de pasta válido conforme `folders-schema-v1.json`.

    :return: dict com os campos obrigatórios de uma entrada de pasta.
    :rtype: dict[str, object]
    """
    return {
        "description": "Forks de repositórios de referência sobre engenharia de agentes",
        "content_type": "repository_forks",
        "license": "unknown",
        "last_scanned": None,
        "status": "pending",
        "path": "/srv/pastas/github_forks",
    }


@pytest.fixture
def fixed_now() -> datetime:
    """
    Relógio fixo em `America/Sao_Paulo` para testes determinísticos.

    :return: datetime com timezone fixa, sem depender do relógio do sistema.
    :rtype: datetime
    """
    return datetime(2026, 9, 21, 15, 55, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
