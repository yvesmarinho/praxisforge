# -*- coding: utf-8 -*-
"""
NOME: test_bootstrap_folders.py
TITULO: Testes de falha — caso de uso bootstrap_folders (fakes)
DATA: 22/09/2026 17:55
MODIFICADO: 22/09/2026 16:47
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.bootstrap_folders
HISTÓRICO:
    - 22/09/2026 17:55: criação (T013)
    - 22/09/2026 18:45: +casos de idempotência (T021, US2)
STATUS: DEV
"""

from pathlib import Path

from praxisforge.application.bootstrap_folders import bootstrap_folders
from praxisforge.application.ports import FolderRegistryRepository, RootFolderProbe
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, registry: FolderRegistry | None = None, exists: bool = True) -> None:
        self._registry = registry or FolderRegistry(schema_version="1", folders={})
        self.save_count = 0
        self._exists = exists

    def load(self) -> FolderRegistry:
        if not self._exists:  # pragma: no cover - defensivo, espelha o adapter real
            raise AssertionError("load() não deve ser chamado quando exists() é False")
        return self._registry

    def load_raw(self) -> dict[str, object]:  # pragma: no cover
        raise NotImplementedError

    def save(self, registry: FolderRegistry) -> None:
        self._registry = registry
        self.save_count += 1
        self._exists = True

    def exists(self) -> bool:
        return self._exists


class _FakeProbe(RootFolderProbe):
    def __init__(
        self,
        subfolders: list[Path],
        descriptions: dict[str, str] | None = None,
        licenses: dict[str, str] | None = None,
    ) -> None:
        self._subfolders = subfolders
        self._descriptions = descriptions or {}
        self._licenses = licenses or {}

    def list_subfolders(self, root: Path) -> list[Path]:
        return self._subfolders

    def read_description(self, path: Path) -> str | None:
        return self._descriptions.get(path.name)

    def detect_license(self, path: Path) -> str | None:
        return self._licenses.get(path.name)


def _paths(tmp_path: Path, *names: str) -> list[Path]:
    resultado = []
    for name in names:
        p = tmp_path / name
        p.mkdir(exist_ok=True)
        resultado.append(p)
    return resultado


def test_subpasta_com_readme_e_license_reconhecivel(tmp_path: Path) -> None:
    """Subpasta com README+LICENSE MIT reconhecível é registrada not_scanned."""
    subpastas = _paths(tmp_path, "repo_a")
    repo = _FakeRepository()
    probe = _FakeProbe(
        subpastas,
        descriptions={"repo_a": "Descrição do repo A"},
        licenses={"repo_a": "MIT"},
    )
    report = bootstrap_folders(repo, probe, tmp_path)
    assert report.registered == ["repo_a"]
    folder = repo.load().get("repo_a")
    assert folder.license == "MIT"
    assert folder.status is CurationStatus.NOT_SCANNED
    assert folder.description == "Descrição do repo A"


def test_subpasta_com_readme_sem_license(tmp_path: Path) -> None:
    """Subpasta com README mas sem LICENSE reconhecível é registrada unknown/pending."""
    subpastas = _paths(tmp_path, "repo_b")
    repo = _FakeRepository()
    probe = _FakeProbe(subpastas, descriptions={"repo_b": "Descrição do repo B"})
    bootstrap_folders(repo, probe, tmp_path)
    folder = repo.load().get("repo_b")
    assert folder.license == "unknown"
    assert folder.status is CurationStatus.PENDING
    assert folder.description == "Descrição do repo B"


def test_subpasta_sem_readme_nem_license(tmp_path: Path) -> None:
    """Subpasta sem README nem LICENSE é registrada com descrição padrão."""
    subpastas = _paths(tmp_path, "repo_c")
    repo = _FakeRepository()
    probe = _FakeProbe(subpastas)
    bootstrap_folders(repo, probe, tmp_path)
    folder = repo.load().get("repo_c")
    assert folder.license == "unknown"
    assert folder.status is CurationStatus.PENDING
    assert folder.description  # não vazia — descrição padrão


def test_raiz_sem_subpastas_nao_levanta(tmp_path: Path) -> None:
    """Pasta-raiz sem subpastas conclui sem erro, 0 registradas."""
    repo = _FakeRepository()
    probe = _FakeProbe([])
    report = bootstrap_folders(repo, probe, tmp_path)
    assert report.registered == []
    assert report.failures == []


def test_colisao_de_alias_entre_duas_subpastas_novas(tmp_path: Path) -> None:
    """Duas subpastas novas que slugificam para o mesmo alias: 1ª registrada, 2ª falha."""
    subpastas = _paths(tmp_path, "Meu-Repo", "meu_repo")
    repo = _FakeRepository()
    probe = _FakeProbe(subpastas)
    report = bootstrap_folders(repo, probe, tmp_path)
    assert len(report.registered) == 1
    assert len(report.failures) == 1
    assert report.failures[0].error_type == "AliasAlreadyRegisteredError"


def test_nome_de_subpasta_nao_vira_alias_valido(tmp_path: Path) -> None:
    """Nome de subpasta que não vira alias válido mesmo slugificado vira falha individual."""
    subpastas = _paths(tmp_path, "9-invalido")
    repo = _FakeRepository()
    probe = _FakeProbe(subpastas)
    report = bootstrap_folders(repo, probe, tmp_path)
    assert report.registered == []
    assert len(report.failures) == 1
    assert report.failures[0].error_type == "InvalidAliasError"


def test_escala_50_subpastas_40_reconheciveis_10_nao(tmp_path: Path) -> None:
    """50 subpastas (40 reconhecíveis, 10 não) são todas registradas sem interromper (SC-003)."""
    nomes = [f"pasta{i:03d}" for i in range(50)]
    subpastas = _paths(tmp_path, *nomes)
    descriptions = {nome: f"Descrição de {nome}" for nome in nomes[:40]}
    licenses = {nome: "MIT" for nome in nomes[:40]}
    repo = _FakeRepository()
    probe = _FakeProbe(subpastas, descriptions=descriptions, licenses=licenses)
    report = bootstrap_folders(repo, probe, tmp_path)
    assert len(report.registered) == 50
    assert report.failures == []
    reconhecidas = [repo.load().get(nome) for nome in nomes[:40]]
    nao_reconhecidas = [repo.load().get(nome) for nome in nomes[40:]]
    assert all(f.license == "MIT" for f in reconhecidas)
    assert all(
        f.license == "unknown" and f.status is CurationStatus.PENDING for f in nao_reconhecidas
    )


def test_bootstrap_nunca_atribui_status_ignore(tmp_path: Path) -> None:
    """Nenhuma pasta registrada pelo bootstrap recebe status ignore (FR-012, garantia nomeada)."""
    nomes = ["repo_a", "repo_b", "repo_c"]
    subpastas = _paths(tmp_path, *nomes)
    repo = _FakeRepository()
    probe = _FakeProbe(subpastas, licenses={"repo_a": "MIT"})
    bootstrap_folders(repo, probe, tmp_path)
    pastas_registradas = [repo.load().get(nome) for nome in nomes]
    assert all(f.status is not CurationStatus.IGNORE for f in pastas_registradas)


# --- US2: idempotência ------------------------------------------------------------------


def test_pasta_ja_registrada_nao_e_alterada(tmp_path: Path) -> None:
    """Pasta cujo alias já existia antes da execução não tem nenhum campo alterado (FR-004)."""
    subpastas = _paths(tmp_path, "repo_a")
    original = Folder(
        alias=Alias("repo_a"),
        description="Descrição curada manualmente",
        content_type="documents",
        license="MIT",
        last_scanned=None,
        status=CurationStatus.CURATED,
    )
    registry = FolderRegistry(schema_version="1", folders={}).add(original)
    repo = _FakeRepository(registry)
    probe = _FakeProbe(subpastas, descriptions={"repo_a": "Descrição nova do bootstrap"})
    report = bootstrap_folders(repo, probe, tmp_path)
    assert report.registered == []
    assert report.skipped_existing == ["repo_a"]
    folder = repo.load().get("repo_a")
    assert folder == original


def test_pasta_ignore_e_pulada_e_nao_reprocessada(tmp_path: Path) -> None:
    """Pasta com status ignore é pulada, contada em skipped_ignored, sem alteração."""
    subpastas = _paths(tmp_path, "pasta_tecnica")
    original = Folder(
        alias=Alias("pasta_tecnica"),
        description="Pasta técnica irrelevante",
        content_type="unclassified",
        license="unknown",
        last_scanned=None,
        status=CurationStatus.IGNORE,
    )
    registry = FolderRegistry(schema_version="1", folders={}).add(original)
    repo = _FakeRepository(registry)
    probe = _FakeProbe(subpastas)
    report = bootstrap_folders(repo, probe, tmp_path)
    assert report.registered == []
    assert report.skipped_ignored == ["pasta_tecnica"]
    assert repo.load().get("pasta_tecnica") == original


def test_resumo_com_registrada_existente_e_ignorada_simultaneamente(tmp_path: Path) -> None:
    """Uma execução com 1 nova + 1 existente + 1 ignore reflete a contagem correta nos 3 grupos."""
    subpastas = _paths(tmp_path, "nova", "existente", "ignorada")
    existente = Folder(
        alias=Alias("existente"),
        description="Já registrada",
        content_type="documents",
        license="MIT",
        last_scanned=None,
        status=CurationStatus.CURATED,
    )
    ignorada = Folder(
        alias=Alias("ignorada"),
        description="Ignorada",
        content_type="unclassified",
        license="unknown",
        last_scanned=None,
        status=CurationStatus.IGNORE,
    )
    registry = FolderRegistry(schema_version="1", folders={}).add(existente).add(ignorada)
    repo = _FakeRepository(registry)
    probe = _FakeProbe(subpastas)
    report = bootstrap_folders(repo, probe, tmp_path)
    assert report.registered == ["nova"]
    assert report.skipped_existing == ["existente"]
    assert report.skipped_ignored == ["ignorada"]
    assert report.failures == []


def test_registro_inexistente_e_tratado_como_vazio(tmp_path: Path) -> None:
    """Primeira execução sem folders.yaml prévio funciona (registro tratado como vazio)."""
    subpastas = _paths(tmp_path, "repo_a")
    repo = _FakeRepository(exists=False)
    probe = _FakeProbe(subpastas)
    report = bootstrap_folders(repo, probe, tmp_path)
    assert report.registered == ["repo_a"]
