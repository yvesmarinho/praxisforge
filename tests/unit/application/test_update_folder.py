# -*- coding: utf-8 -*-
"""
NOME: test_update_folder.py
TITULO: Testes de falha — caso de uso update_folder (repositório fake)
DATA: 22/09/2026 09:45
MODIFICADO: 25/09/2026 09:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.update_folder
HISTÓRICO:
    - 22/09/2026 09:45: criação (T031)
    - 22/09/2026 19:00: +caso status ignore (T027, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:08: resolver/inspector + testes de versão curada (T018, T023, feature 004)
    - 23/09/2026 16:52: FolderLocator + path (T020, feature 005)
    - 25/09/2026 09:52: +casos --description
STATUS: DEV
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from praxisforge.application.dto import UpdateFolderInput
from praxisforge.application.ports import (
    FolderLocator,
    FolderRegistryRepository,
    GitContentInspector,
)
from praxisforge.application.update_folder import UpdateFolderResult
from praxisforge.application.update_folder import update_folder as _update_folder
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    ContentInspectionError,
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathUnreadableError,
    UnknownLicenseRequiresPendingError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, registry: FolderRegistry) -> None:
        self._registry = registry
        self.save_count = 0

    def load(self) -> FolderRegistry:
        return self._registry

    def load_raw(self) -> dict[str, object]:  # pragma: no cover
        raise NotImplementedError

    def save(self, registry: FolderRegistry) -> None:
        self._registry = registry
        self.save_count += 1

    def exists(self) -> bool:
        return True


class _FakeResolver(FolderLocator):
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.calls = 0

    def check(self, alias: str, path: Path) -> Path:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return path

    def canonicalize(self, alias: str, raw: str) -> Path:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return Path(raw.rstrip("/") or "/")


class _FakeInspector(GitContentInspector):
    def __init__(self, head: str | None = "a" * 40, error: Exception | None = None) -> None:
        self._head = head
        self._error = error
        self.calls = 0

    def head_commit(self, path: Path) -> str | None:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._head

    def changed_since(self, path: Path, commit: str) -> bool:  # pragma: no cover
        raise AssertionError("update_folder não compara conteúdo")


class _ProibidoResolver(FolderLocator):
    def check(self, alias: str, path: Path) -> Path:  # pragma: no cover - falha se chamado
        raise AssertionError("status != curated não deve conferir o caminho")

    def canonicalize(self, alias: str, raw: str) -> Path:  # pragma: no cover
        raise AssertionError("sem --path não deve canonizar")


class _ProibidoInspector(GitContentInspector):
    def head_commit(self, path: Path) -> str | None:  # pragma: no cover
        raise AssertionError("status != curated não deve consultar o git")

    def changed_since(self, path: Path, commit: str) -> bool:  # pragma: no cover
        raise AssertionError("status != curated não deve consultar o git")


def update_folder(repository: FolderRegistryRepository, data: UpdateFolderInput) -> Folder:
    """Casos da feature 001: nenhum marca curated, então git nunca é consultado (FR-010)."""
    result = _update_folder(
        repository, data, locator=_ProibidoResolver(), inspector=_ProibidoInspector()
    )
    assert result.head_recorded is None
    return result.folder


def _registry() -> FolderRegistry:
    reg = FolderRegistry(schema_version="2", folders={})
    return reg.add(
        Folder(
            alias=Alias("github_forks"),
            description="Forks",
            content_type="repository_forks",
            license="unknown",
            last_scanned=None,
            status=CurationStatus.PENDING,
            path="/srv/pastas/github_forks",
        )
    )


def test_atualiza_so_os_campos_informados() -> None:
    """update_folder altera só os campos informados, mantendo os demais."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT"))
    folder = repo.load().get("github_forks")
    assert folder.license == "MIT"
    assert folder.description == "Forks"


def test_atomico_grava_uma_vez() -> None:
    """update_folder grava atomicamente (uma única escrita por chamada)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT"))
    assert repo.save_count == 1


def test_last_scanned_futuro_recusado() -> None:
    """last_scanned no futuro é recusado."""
    repo = _FakeRepository(_registry())
    futuro = (datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(days=1)).isoformat()
    with pytest.raises(Exception):  # noqa: B017 - FutureScanDateError ou ValidationError do DTO
        update_folder(
            repo,
            UpdateFolderInput(alias="github_forks", license="MIT", last_scanned=futuro),
        )


def test_licenca_unknown_mantida_com_status_diferente_de_pending_recusada() -> None:
    """Tentar mudar status sem resolver a licença unknown é recusado."""
    repo = _FakeRepository(_registry())
    with pytest.raises(UnknownLicenseRequiresPendingError):
        update_folder(repo, UpdateFolderInput(alias="github_forks", status="scanned"))


def test_licenca_valida_e_novo_status_na_mesma_operacao_aceita() -> None:
    """Licença válida + novo status na mesma chamada é aceito (spec cenário 5)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT", status="scanned"))
    folder = repo.load().get("github_forks")
    assert folder.license == "MIT"
    assert folder.status is CurationStatus.SCANNED


def test_alias_inexistente_levanta_erro() -> None:
    """update_folder de alias inexistente levanta FolderNotFoundError."""
    repo = _FakeRepository(_registry())
    with pytest.raises(FolderNotFoundError):
        update_folder(repo, UpdateFolderInput(alias="inexistente", license="MIT"))


def test_repetir_mesmo_update_nao_altera_bytes_conceitualmente() -> None:
    """Repetir o mesmo update produz o mesmo estado final (idempotente em efeito)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT", status="scanned"))
    estado_1 = repo.load().get("github_forks")
    update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT", status="scanned"))
    estado_2 = repo.load().get("github_forks")
    assert estado_1 == estado_2


def test_log_estruturado_sem_caminho_absoluto(caplog: pytest.LogCaptureFixture) -> None:
    """update_folder emite log estruturado (evento, alias, resultado) sem caminho absoluto."""
    repo = _FakeRepository(_registry())
    with caplog.at_level(logging.INFO):
        update_folder(repo, UpdateFolderInput(alias="github_forks", license="MIT"))
    assert caplog.records
    for record in caplog.records:
        assert "/home/" not in record.message


def test_status_ignore_aceito_com_licenca_unknown() -> None:
    """update_folder aceita status='ignore' mesmo com licença unknown (FR-011)."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", status="ignore"))
    folder = repo.load().get("github_forks")
    assert folder.status is CurationStatus.IGNORE
    assert folder.license == "unknown"


# --- feature 004: versão curada (US1) --------------------------------------------------


def _registry_mit(
    commit: str | None = None, status: CurationStatus = CurationStatus.SCANNED
) -> FolderRegistry:
    agora = datetime.now(ZoneInfo("America/Sao_Paulo")) - timedelta(minutes=5)
    return FolderRegistry(schema_version="2", folders={}).add(
        Folder(
            alias=Alias("repo"),
            description="Repositório",
            content_type="repository_forks",
            license="MIT",
            last_scanned=agora,
            status=status,
            path="/srv/pastas/repo",
            last_curated_commit=commit,
        )
    )


def _curar(
    repo: _FakeRepository, resolver: FolderLocator, inspector: GitContentInspector
) -> UpdateFolderResult:
    return _update_folder(
        repo,
        UpdateFolderInput(alias="repo", status="curated"),
        locator=resolver,
        inspector=inspector,
    )


def test_marcar_curada_em_pasta_git_grava_head() -> None:
    """status → curated grava o HEAD atual (FR-001)."""
    repo = _FakeRepository(_registry_mit())
    result = _curar(repo, _FakeResolver(), _FakeInspector(head="b" * 40))
    assert result.head_recorded is True
    assert result.folder.status is CurationStatus.CURATED
    assert repo.load().get("repo").last_curated_commit == "b" * 40


def test_marcar_curada_em_pasta_nao_git_nao_grava() -> None:
    """Pasta não-git: status muda, nenhuma versão gravada (FR-002)."""
    repo = _FakeRepository(_registry_mit())
    result = _curar(repo, _FakeResolver(), _FakeInspector(head=None))
    assert result.head_recorded is False
    assert result.folder.status is CurationStatus.CURATED
    assert result.folder.last_curated_commit is None


def test_marcar_curada_nao_git_mantem_hash_anterior() -> None:
    """Pasta não-git com hash antigo mantém o hash (FR-016)."""
    repo = _FakeRepository(_registry_mit(commit="c" * 40, status=CurationStatus.IN_CURATION))
    result = _curar(repo, _FakeResolver(), _FakeInspector(head=None))
    assert result.head_recorded is False
    assert result.folder.last_curated_commit == "c" * 40


def test_remarcar_curada_atualiza_hash() -> None:
    """Pasta revertida e revisada: remarcar curada grava o HEAD novo (US1 cenário 3)."""
    repo = _FakeRepository(_registry_mit(commit="c" * 40, status=CurationStatus.IN_CURATION))
    result = _curar(repo, _FakeResolver(), _FakeInspector(head="d" * 40))
    assert result.folder.last_curated_commit == "d" * 40


def test_remarcar_curada_sem_commit_novo_informa_hash_gravado() -> None:
    """Mesmo HEAD já gravado: head_recorded continua True (não confunde com não-git)."""
    repo = _FakeRepository(_registry_mit(commit="d" * 40, status=CurationStatus.CURATED))
    result = _curar(repo, _FakeResolver(), _FakeInspector(head="d" * 40))
    assert result.head_recorded is True
    assert result.folder.last_curated_commit == "d" * 40


def test_outro_status_preserva_hash_e_nao_consulta_git() -> None:
    """status != curated não toca no git e mantém o hash como histórico (FR-010)."""
    repo = _FakeRepository(_registry_mit(commit="c" * 40, status=CurationStatus.CURATED))
    folder = update_folder(repo, UpdateFolderInput(alias="repo", status="in_curation"))
    assert folder.status is CurationStatus.IN_CURATION
    assert folder.last_curated_commit == "c" * 40


@pytest.mark.parametrize(
    "error",
    [FolderPathUnreadableError("repo"), FolderPathInvalidError("repo", "não existe")],
    ids=["sem_permissao", "movida"],
)
def test_caminho_inacessivel_falha_sem_salvar(error: Exception) -> None:
    """Caminho inacessível ao marcar curada → exceção e registro intocado (FR-003)."""
    repo = _FakeRepository(_registry_mit())
    inspector = _FakeInspector()
    with pytest.raises(type(error)):
        _curar(repo, _FakeResolver(error=error), inspector)
    assert repo.save_count == 0
    assert inspector.calls == 0
    assert repo.load().get("repo").status is CurationStatus.SCANNED


def test_falha_do_git_ao_marcar_curada_nao_salva() -> None:
    """ContentInspectionError → propagada com alias e registro intocado (FR-009)."""
    repo = _FakeRepository(_registry_mit())
    with pytest.raises(ContentInspectionError) as info:
        _curar(
            repo,
            _FakeResolver(),
            _FakeInspector(error=ContentInspectionError("", "tempo esgotado")),
        )
    assert info.value.alias == "repo"
    assert repo.save_count == 0


# --- feature 005: atualizar caminho (FR-016) --------------------------------------------


def test_update_path_canoniza_e_preserva_demais_dados() -> None:
    """--path grava o caminho canônico e mantém status/licença/versão curada."""
    repo = _FakeRepository(_registry_mit(commit="c" * 40, status=CurationStatus.CURATED))
    result = _update_folder(
        repo,
        UpdateFolderInput(alias="repo", path="/srv/nova/repo/"),
        locator=_FakeResolver(),
        inspector=_ProibidoInspector(),
    )
    assert result.folder.path == "/srv/nova/repo"
    assert result.folder.status is CurationStatus.CURATED
    assert result.folder.last_curated_commit == "c" * 40
    assert repo.save_count == 1


def test_update_path_duplicado_nao_salva() -> None:
    """Caminho já usado por outra pasta → PathAlreadyRegisteredError, nada salvo."""
    from praxisforge.domain.errors import PathAlreadyRegisteredError

    registry = _registry_mit().add(
        Folder(
            alias=Alias("outra"),
            description="Outra",
            content_type="documents",
            license="MIT",
            last_scanned=None,
            status=CurationStatus.NOT_SCANNED,
            path="/srv/outra",
        )
    )
    repo = _FakeRepository(registry)
    with pytest.raises(PathAlreadyRegisteredError) as info:
        _update_folder(
            repo,
            UpdateFolderInput(alias="repo", path="/srv/outra"),
            locator=_FakeResolver(),
            inspector=_ProibidoInspector(),
        )
    assert info.value.owner == "outra"
    assert repo.save_count == 0


def test_update_path_inexistente_nao_salva() -> None:
    """Locator recusa o caminho → exceção propagada, nada salvo (FR-004)."""
    repo = _FakeRepository(_registry_mit())
    with pytest.raises(FolderPathInvalidError):
        _update_folder(
            repo,
            UpdateFolderInput(alias="repo", path="/nao/existe"),
            locator=_FakeResolver(error=FolderPathInvalidError("repo", "caminho inexistente")),
            inspector=_ProibidoInspector(),
        )
    assert repo.save_count == 0


def test_update_de_licenca_em_pasta_curada_nao_regrava_versao() -> None:
    """Regressão: só --status curated grava o HEAD; editar outro campo preserva a versão."""
    repo = _FakeRepository(_registry_mit(commit="c" * 40, status=CurationStatus.CURATED))
    result = _update_folder(
        repo,
        UpdateFolderInput(alias="repo", license="Apache-2.0"),
        locator=_ProibidoResolver(),
        inspector=_ProibidoInspector(),
    )
    assert result.head_recorded is None
    assert result.folder.last_curated_commit == "c" * 40


# --- folders update --description -------------------------------------------------------


def test_update_description_grava_e_preserva_demais() -> None:
    """--description troca a descrição, preserva o resto e grava uma vez."""
    repo = _FakeRepository(_registry())
    update_folder(repo, UpdateFolderInput(alias="github_forks", description="Forks de agentes"))
    folder = repo.load().get("github_forks")
    assert folder.description == "Forks de agentes"
    assert folder.license == "unknown"
    assert repo.save_count == 1


@pytest.mark.parametrize("descricao", ["", "x" * 501])
def test_description_fora_do_contrato_recusada_no_dto(descricao: str) -> None:
    """Descrição vazia ou acima de 500 caracteres falha já na entrada (fail fast)."""
    with pytest.raises(ValidationError):
        UpdateFolderInput(alias="github_forks", description=descricao)
