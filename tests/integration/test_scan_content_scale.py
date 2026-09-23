# -*- coding: utf-8 -*-
"""
NOME: test_scan_content_scale.py
TITULO: Teste de escala — varredura em lote com verificação de conteúdo git
DATA: 23/09/2026 12:18
MODIFICADO: 23/09/2026 12:19
VERSÃO: 0.1.0
DEPEND: pytest, git (executável), praxisforge.application.scan_folders
HISTÓRICO:
    - 23/09/2026 12:18: criação (T041, feature 004-deteccao-mudanca-conteudo)
STATUS: DEV
"""

import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from praxisforge.application.scan_folders import ContentCheck, scan_all_folders
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry
from praxisforge.infrastructure.env_path_resolver import EnvPathResolver
from praxisforge.infrastructure.git_cli_inspector import GitCliInspector
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.yaml_folder_registry import YamlFolderRegistryRepository

_TOTAL = 100
_LIMITE_SEGUNDOS = 30.0
_SCHEMAS_DIR = Path(__file__).parents[2] / "schemas"
_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Teste",
    "GIT_AUTHOR_EMAIL": "teste@example.invalid",
    "GIT_COMMITTER_NAME": "Teste",
    "GIT_COMMITTER_EMAIL": "teste@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **_GIT_ENV},
    )
    return result.stdout.strip()


def _commit(repo: Path, conteudo: str) -> str:
    (repo / "dados.txt").write_text(conteudo, encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-q", "-m", conteudo)
    return _git(repo, "rev-parse", "HEAD")


def test_lote_de_100_pastas_curadas_em_menos_de_30s(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """100 curadas, metade alteradas: só as alteradas são revertidas (SC-001, SC-003)."""
    registry = FolderRegistry(schema_version="1", folders={})
    alteradas: set[str] = set()
    for indice in range(_TOTAL):
        alias = f"fonte_{indice:03d}"
        repo = tmp_path / alias
        repo.mkdir()
        _git(repo, "init", "-q")
        gravado = _commit(repo, "v1")
        if indice % 2 == 0:
            _commit(repo, "v2")
            alteradas.add(alias)
        monkeypatch.setenv(f"PRAXISFORGE_FOLDER_{alias.upper()}", str(repo))
        registry = registry.add(
            Folder(
                alias=Alias(alias),
                description=f"Fonte {indice}",
                content_type="documents",
                license="MIT",
                last_scanned=datetime(2026, 9, 1, tzinfo=UTC),
                status=CurationStatus.CURATED,
                last_curated_commit=gravado,
            )
        )
    repository = YamlFolderRegistryRepository(
        tmp_path / "folders.yaml", JsonSchemaContractValidator(_SCHEMAS_DIR)
    )
    repository.save(registry)

    inicio = time.perf_counter()
    report = scan_all_folders(repository, EnvPathResolver(), inspector=GitCliInspector())
    duracao = time.perf_counter() - inicio

    assert duracao < _LIMITE_SEGUNDOS
    assert report.failures == []
    assert set(report.reverted) == alteradas
    inalteradas = {r.alias for r in report.ok if r.content_check is ContentCheck.UNCHANGED}
    assert len(inalteradas) == _TOTAL - len(alteradas)
