# -*- coding: utf-8 -*-
"""
NOME: test_migrate_registry.py
TITULO: Testes de falha — migrar registro v1 → v2 (caminho absoluto)
DATA: 23/09/2026 17:02
MODIFICADO: 23/09/2026 17:02
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.migrate_registry
HISTÓRICO:
    - 23/09/2026 17:02: criação (T032, feature 005-caminho-absoluto-registro)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.application.migrate_registry import migrate_registry
from praxisforge.application.ports import (
    FolderLocator,
    FolderRegistryRepository,
    LegacyPathSource,
    RootFolderProbe,
)
from praxisforge.domain.errors import FolderPathInvalidError, RegistryFileNotFoundError
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, raw: dict[str, object] | None) -> None:
        self._raw = raw
        self.saved: FolderRegistry | None = None

    def load(self) -> FolderRegistry:  # pragma: no cover - migração usa load_raw
        raise AssertionError("migração não deve usar load()")

    def load_raw(self) -> dict[str, object]:
        if self._raw is None:
            raise RegistryFileNotFoundError
        return self._raw

    def save(self, registry: FolderRegistry) -> None:
        self.saved = registry

    def exists(self) -> bool:
        return self._raw is not None


class _FakeLegacy(LegacyPathSource):
    def __init__(self, caminhos: dict[str, str] | None = None) -> None:
        self._caminhos = caminhos or {}

    def lookup(self, alias: str) -> str | None:
        return self._caminhos.get(alias)


class _FakeLocator(FolderLocator):
    def canonicalize(self, alias: str, raw: str) -> Path:
        caminho = Path(raw).expanduser()
        if not caminho.is_dir():
            raise FolderPathInvalidError(alias, "caminho inexistente")
        return caminho.resolve()

    def check(self, alias: str, path: Path) -> Path:  # pragma: no cover
        return path


class _FakeProbe(RootFolderProbe):
    """Lista as subpastas reais da raiz (tmp_path)."""

    def list_subfolders(self, root: Path) -> list[Path]:
        return sorted(p for p in root.iterdir() if p.is_dir())

    def read_description(self, path: Path) -> str | None:  # pragma: no cover
        return None

    def detect_license(self, path: Path) -> str | None:  # pragma: no cover
        return None


def _entrada(
    status: str = "not_scanned", license: str = "MIT", **extra: object
) -> dict[str, object]:  # noqa: A002
    entrada: dict[str, object] = {
        "description": "d",
        "content_type": "documents",
        "license": license,
        "last_scanned": None,
        "status": status,
    }
    entrada.update(extra)
    return entrada


def _v1(**folders: dict[str, object]) -> dict[str, object]:
    return {"schema_version": "1", "folders": dict(folders)}


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    pasta = tmp_path / "github_forks"
    for nome in ("graphify", "Meu-Repo", "agents"):
        (pasta / nome).mkdir(parents=True)
    return pasta


def test_caminho_da_variavel_tem_prioridade(raiz: Path, tmp_path: Path) -> None:
    """(1) variável antiga; (2) raiz — FR-014."""
    outra = tmp_path / "outra_graphify"
    outra.mkdir()
    repo = _FakeRepository(_v1(graphify=_entrada()))
    report = migrate_registry(
        repo, _FakeLegacy({"graphify": str(outra)}), _FakeLocator(), probe=_FakeProbe(), root=raiz
    )
    assert report.written is True
    assert repo.saved is not None
    assert repo.saved.get("graphify").path == str(outra.resolve())


def test_caminho_pela_raiz_quando_nao_ha_variavel(raiz: Path) -> None:
    """Subpasta da raiz cujo nome normalizado bate com o alias (Meu-Repo → meu_repo)."""
    repo = _FakeRepository(_v1(meu_repo=_entrada(), graphify=_entrada()))
    report = migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=raiz)
    assert sorted(report.migrated) == ["graphify", "meu_repo"]
    assert repo.saved is not None
    assert repo.saved.get("meu_repo").path == str((raiz / "Meu-Repo").resolve())
    assert repo.saved.schema_version == "2"


def test_preserva_alias_e_todos_os_campos(raiz: Path) -> None:
    """Todos os campos e a versão curada preservados (FR-010)."""
    entrada = _entrada(
        status="curated",
        last_scanned="2026-09-20T10:00:00-03:00",
        last_curated_commit="a" * 40,
    )
    repo = _FakeRepository(_v1(graphify=entrada))
    migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=raiz)
    assert repo.saved is not None
    folder = repo.saved.get("graphify")
    assert folder.status.value == "curated"
    assert folder.last_curated_commit == "a" * 40
    assert folder.last_scanned is not None
    assert folder.description == "d"


def test_pendencia_impede_gravacao(raiz: Path) -> None:
    """Pasta sem caminho encontrado → pendência, nada gravado (FR-011)."""
    repo = _FakeRepository(_v1(graphify=_entrada(), sumida=_entrada()))
    report = migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=raiz)
    assert report.written is False
    assert repo.saved is None
    assert [p.alias for p in report.pending] == ["sumida"]
    assert report.migrated == ["graphify"]


def test_sem_raiz_e_sem_variavel_vira_pendencia() -> None:
    """Sem --root, só as variáveis contam."""
    repo = _FakeRepository(_v1(graphify=_entrada()))
    report = migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=None)
    assert [p.alias for p in report.pending] == ["graphify"]
    assert repo.saved is None


def test_variavel_apontando_para_caminho_inexistente_vira_pendencia(raiz: Path) -> None:
    """Variável inválida não cai para a raiz silenciosamente: vira pendência com motivo."""
    repo = _FakeRepository(_v1(graphify=_entrada()))
    report = migrate_registry(
        repo,
        _FakeLegacy({"graphify": "/nao/existe"}),
        _FakeLocator(),
        probe=_FakeProbe(),
        root=raiz,
    )
    assert report.pending[0].error_type == "FolderPathInvalidError"


def test_dois_candidatos_na_raiz_viram_pendencia(tmp_path: Path) -> None:
    """'a-b' e 'a_b' na raiz → ambíguo para o alias a_b."""
    raiz = tmp_path / "forks"
    (raiz / "a-b").mkdir(parents=True)
    (raiz / "a_b").mkdir()
    repo = _FakeRepository(_v1(a_b=_entrada()))
    report = migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=raiz)
    assert [p.alias for p in report.pending] == ["a_b"]
    assert "ambíg" in report.pending[0].message


def test_raiz_registrada_como_pasta_e_removida(raiz: Path) -> None:
    """Entrada cujo caminho é ancestral de outras é removida (FR-017)."""
    repo = _FakeRepository(
        _v1(
            github_forks=_entrada(status="pending", license="unknown"),
            graphify=_entrada(),
            agents=_entrada(),
        )
    )
    report = migrate_registry(
        repo,
        _FakeLegacy({"github_forks": str(raiz)}),
        _FakeLocator(),
        probe=_FakeProbe(),
        root=raiz,
    )
    assert report.removed_roots == ["github_forks"]
    assert report.written is True
    assert repo.saved is not None
    assert "github_forks" not in repo.saved.folders
    assert sorted(repo.saved.folders) == ["agents", "graphify"]


def test_caminhos_duplicados_viram_pendencia(raiz: Path) -> None:
    """Dois aliases resolvidos para o mesmo caminho → pendência para o segundo."""
    repo = _FakeRepository(_v1(graphify=_entrada(), outro=_entrada()))
    report = migrate_registry(
        repo,
        _FakeLegacy({"outro": str(raiz / "graphify")}),
        _FakeLocator(),
        probe=_FakeProbe(),
        root=raiz,
    )
    assert [p.alias for p in report.pending] == ["outro"]
    assert report.pending[0].error_type == "PathAlreadyRegisteredError"
    assert repo.saved is None


def test_registro_ja_v2_nao_muda_nada(raiz: Path) -> None:
    """Idempotência (FR-011, SC-005)."""
    repo = _FakeRepository({"schema_version": "2", "folders": {}})
    report = migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=raiz)
    assert report.already_current is True
    assert report.written is False
    assert repo.saved is None


def test_registro_inexistente_levanta() -> None:
    """Sem registro não há o que migrar."""
    with pytest.raises(RegistryFileNotFoundError):
        migrate_registry(
            _FakeRepository(None), _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=None
        )


def test_entrada_v1_invalida_vira_pendencia(raiz: Path) -> None:
    """Entrada que viola regras (ex.: status 'ignored') é pendência com o motivo."""
    repo = _FakeRepository(_v1(graphify=_entrada(status="ignored")))
    report = migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=raiz)
    assert [p.alias for p in report.pending] == ["graphify"]
    assert repo.saved is None


def test_raiz_reconhecida_pelo_nome_sem_variavel_e_removida(raiz: Path) -> None:
    """Alias igual ao nome da raiz, sem variável → é a própria raiz → removida (FR-017)."""
    repo = _FakeRepository(
        _v1(github_forks=_entrada(status="pending", license="unknown"), graphify=_entrada())
    )
    report = migrate_registry(repo, _FakeLegacy(), _FakeLocator(), probe=_FakeProbe(), root=raiz)
    assert report.removed_roots == ["github_forks"]
    assert report.pending == []
    assert report.migrated == ["graphify"]
