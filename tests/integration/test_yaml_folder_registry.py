# -*- coding: utf-8 -*-
"""
NOME: test_yaml_folder_registry.py
TITULO: Testes de falha — adapter YamlFolderRegistryRepository (Infrastructure)
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 12:04
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.yaml_folder_registry
HISTÓRICO:
    - 22/09/2026 09:45: criação (T028)
    - 23/09/2026 12:04: +last_curated_commit (T006, feature 004)
STATUS: DEV
"""

import os
import stat
from pathlib import Path

import pytest

from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import RegistryFileNotFoundError, RegistryUnavailableError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.yaml_folder_registry import YamlFolderRegistryRepository

_SCHEMAS_DIR = Path(__file__).parents[2] / "schemas"


def _repo(path: Path) -> YamlFolderRegistryRepository:
    return YamlFolderRegistryRepository(path, JsonSchemaContractValidator(_SCHEMAS_DIR))


def _registry_com_github_forks() -> FolderRegistry:
    folder = Folder(
        alias=Alias("github_forks"),
        description="Forks de repositórios de referência",
        content_type="repository_forks",
        license="unknown",
        last_scanned=None,
        status=CurationStatus.PENDING,
    )
    return FolderRegistry(schema_version="1", folders={}).add(folder)


def test_save_load_ida_e_volta(tmp_registry_path: Path) -> None:
    """save seguido de load reconstrói o mesmo agregado."""
    repo = _repo(tmp_registry_path)
    registry = _registry_com_github_forks()
    repo.save(registry)
    loaded = repo.load()
    assert loaded.get("github_forks") == registry.get("github_forks")


def test_escrita_determinística(tmp_registry_path: Path) -> None:
    """Regravar o mesmo registro produz bytes idênticos."""
    repo = _repo(tmp_registry_path)
    registry = _registry_com_github_forks()
    repo.save(registry)
    primeira = tmp_registry_path.read_bytes()
    repo.save(registry)
    segunda = tmp_registry_path.read_bytes()
    assert primeira == segunda


def test_escrita_atomica_falha_no_meio_preserva_original(
    tmp_registry_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Uma falha simulada em os.replace mantém o arquivo original íntegro."""
    repo = _repo(tmp_registry_path)
    registry = _registry_com_github_forks()
    repo.save(registry)
    original = tmp_registry_path.read_bytes()

    def _falha(*_args: object, **_kwargs: object) -> None:
        raise OSError("falha simulada")

    monkeypatch.setattr(os, "replace", _falha)
    updated = registry.update("github_forks", status=CurationStatus.PENDING, license="MIT")
    with pytest.raises(OSError):
        repo.save(updated)
    assert tmp_registry_path.read_bytes() == original


def test_arquivo_ausente_levanta_registry_file_not_found(tmp_registry_path: Path) -> None:
    """load de um arquivo ausente levanta RegistryFileNotFoundError."""
    repo = _repo(tmp_registry_path)
    with pytest.raises(RegistryFileNotFoundError):
        repo.load()


def test_yaml_corrompido_levanta_registry_unavailable(tmp_registry_path: Path) -> None:
    """YAML corrompido levanta RegistryUnavailableError com arquivo/linha."""
    tmp_registry_path.write_text("schema_version: 1\nfolders: [invalido: : :\n", encoding="utf-8")
    repo = _repo(tmp_registry_path)
    with pytest.raises(RegistryUnavailableError):
        repo.load()


def test_permissao_negada_levanta_registry_unavailable(tmp_registry_path: Path) -> None:
    """Arquivo sem permissão de leitura levanta RegistryUnavailableError."""
    repo = _repo(tmp_registry_path)
    repo.save(_registry_com_github_forks())
    tmp_registry_path.chmod(0o000)
    try:
        if os.access(tmp_registry_path, os.R_OK):
            pytest.skip("ambiente executa como root; permissão não é aplicável")
        with pytest.raises(RegistryUnavailableError):
            repo.load()
    finally:
        tmp_registry_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_add_em_arquivo_ausente_cria_o_arquivo(tmp_registry_path: Path) -> None:
    """add (via save) em arquivo ausente cria o arquivo com folders: {} se vazio."""
    repo = _repo(tmp_registry_path)
    assert not repo.exists()
    registry = FolderRegistry(schema_version="1", folders={})
    repo.save(registry)
    assert repo.exists()
    loaded = repo.load()
    assert loaded.list() == []


def test_last_scanned_preenchido_sobrevive_ida_e_volta_como_string(
    tmp_registry_path: Path, fixed_now: object
) -> None:
    """last_scanned sobrevive a save→load como string ISO idêntica, com bytes estáveis."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    now = datetime(2026, 9, 21, 15, 55, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    folder = Folder(
        alias=Alias("github_forks"),
        description="Forks de repositórios de referência",
        content_type="repository_forks",
        license="MIT",
        last_scanned=now,
        status=CurationStatus.SCANNED,
    )
    registry = FolderRegistry(schema_version="1", folders={}).add(folder)
    repo = _repo(tmp_registry_path)
    repo.save(registry)
    conteudo = tmp_registry_path.read_text(encoding="utf-8")
    assert "2026-09-21T15:55:00-03:00" in conteudo
    loaded = repo.load()
    assert loaded.get("github_forks").last_scanned == now
    primeira = tmp_registry_path.read_bytes()
    repo.save(loaded)
    assert tmp_registry_path.read_bytes() == primeira


def test_last_curated_commit_sobrevive_ida_e_volta(tmp_registry_path: Path) -> None:
    """O hash gravado é persistido e relido sem perda."""
    repo = _repo(tmp_registry_path)
    registry = _registry_com_github_forks().update(
        "github_forks", license="MIT", last_curated_commit="d" * 40
    )
    repo.save(registry)
    assert repo.load().get("github_forks").last_curated_commit == "d" * 40


def test_chave_omitida_no_yaml_quando_none(tmp_registry_path: Path) -> None:
    """Sem hash, a chave não aparece no YAML — registros antigos não ganham diff (FR-012)."""
    repo = _repo(tmp_registry_path)
    repo.save(_registry_com_github_forks())
    assert "last_curated_commit" not in tmp_registry_path.read_text(encoding="utf-8")
    assert repo.load().get("github_forks").last_curated_commit is None


def test_yaml_com_hash_invalido_falha_na_validacao(tmp_registry_path: Path) -> None:
    """Registro com hash malformado é rejeitado pelo contrato ao carregar."""
    from praxisforge.domain.errors import ContractValidationError

    tmp_registry_path.write_text(
        "schema_version: '1'\n"
        "folders:\n"
        "  github_forks:\n"
        "    description: Forks\n"
        "    content_type: repository_forks\n"
        "    license: MIT\n"
        "    last_scanned: null\n"
        "    status: curated\n"
        "    last_curated_commit: NAO_EH_HASH\n",
        encoding="utf-8",
    )
    with pytest.raises(ContractValidationError):
        _repo(tmp_registry_path).load()
