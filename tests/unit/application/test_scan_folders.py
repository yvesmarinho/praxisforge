# -*- coding: utf-8 -*-
"""
NOME: test_scan_folders.py
TITULO: Testes de falha — casos de uso scan_folder e scan_all_folders (fakes)
DATA: 22/09/2026 12:35
MODIFICADO: 22/09/2026 12:05
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.scan_folders
HISTÓRICO:
    - 22/09/2026 12:35: criação (T002/T008/T014)
STATUS: DEV
"""

import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from praxisforge.application.ports import FolderRegistryRepository, PathResolver
from praxisforge.application.scan_folders import scan_all_folders, scan_folder
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    FolderNotFoundError,
    FolderPathInvalidError,
    FolderPathNotConfiguredError,
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


class _FakeResolver(PathResolver):
    def __init__(
        self, paths: dict[str, Path], broken: Mapping[str, Exception] | None = None
    ) -> None:
        self._paths = paths
        self._broken = broken or {}

    def resolve(self, alias: str) -> Path:
        if alias in self._broken:
            raise self._broken[alias]
        if alias not in self._paths:
            raise FolderPathNotConfiguredError(alias)
        return self._paths[alias]


def _folder(alias: str, status: CurationStatus, license: str = "MIT") -> Folder:  # noqa: A002
    return Folder(
        alias=Alias(alias),
        description=f"Descrição de {alias}",
        content_type="documents",
        license=license,
        last_scanned=None,
        status=status,
    )


def _registry(*folders: Folder) -> FolderRegistry:
    reg = FolderRegistry(schema_version="1", folders={})
    for folder in folders:
        reg = reg.add(folder)
    return reg


# --- US1: scan_folder ---------------------------------------------------------------


def test_pasta_nao_varrida_avanca_para_varrida(tmp_path: Path) -> None:
    """Pasta 'não varrida' com caminho válido avança para 'varrida' e recebe last_scanned."""
    repo = _FakeRepository(_registry(_folder("demo_a", CurationStatus.NOT_SCANNED)))
    resolver = _FakeResolver({"demo_a": tmp_path})
    resultado = scan_folder(repo, resolver, "demo_a")
    assert resultado.status is CurationStatus.SCANNED
    assert resultado.last_scanned is not None
    folder = repo.load().get("demo_a")
    assert folder.status is CurationStatus.SCANNED
    assert folder.last_scanned == resultado.last_scanned


@pytest.mark.parametrize(
    "status",
    [CurationStatus.SCANNED, CurationStatus.IN_CURATION, CurationStatus.CURATED],
)
def test_pasta_em_outro_status_mantem_status_so_atualiza_last_scanned(
    tmp_path: Path, status: CurationStatus
) -> None:
    """Pasta com status != não-varrida mantém o status; só last_scanned avança."""
    repo = _FakeRepository(_registry(_folder("demo_a", status)))
    resolver = _FakeResolver({"demo_a": tmp_path})
    resultado = scan_folder(repo, resolver, "demo_a")
    assert resultado.status is status
    folder = repo.load().get("demo_a")
    assert folder.status is status
    assert folder.last_scanned is not None


def test_pasta_pendente_permanece_pendente_apos_varrer(tmp_path: Path) -> None:
    """Pasta 'pendente' (licença unknown) permanece pendente após a varredura (edge case spec)."""
    repo = _FakeRepository(
        _registry(_folder("demo_a", CurationStatus.PENDING, license="unknown"))
    )
    resolver = _FakeResolver({"demo_a": tmp_path})
    resultado = scan_folder(repo, resolver, "demo_a")
    assert resultado.status is CurationStatus.PENDING
    folder = repo.load().get("demo_a")
    assert folder.status is CurationStatus.PENDING
    assert folder.license == "unknown"
    assert folder.last_scanned is not None


def test_varredura_nao_altera_description_content_type_license(tmp_path: Path) -> None:
    """Varredura não altera description/content_type/license (FR-011)."""
    original = _folder("demo_a", CurationStatus.NOT_SCANNED)
    repo = _FakeRepository(_registry(original))
    resolver = _FakeResolver({"demo_a": tmp_path})
    scan_folder(repo, resolver, "demo_a")
    folder = repo.load().get("demo_a")
    assert folder.description == original.description
    assert folder.content_type == original.content_type
    assert folder.license == original.license


def test_alias_nao_registrado_levanta_erro_sem_consultar_ambiente(tmp_path: Path) -> None:
    """Alias não registrado levanta FolderNotFoundError sem consultar o resolver nem salvar."""
    repo = _FakeRepository(_registry())
    resolver = _FakeResolver({"demo_a": tmp_path})
    with pytest.raises(FolderNotFoundError):
        scan_folder(repo, resolver, "inexistente")
    assert repo.save_count == 0


def test_falha_de_caminho_nao_altera_registro() -> None:
    """Falha ao resolver o caminho propaga a exceção e não altera o registro."""
    repo = _FakeRepository(_registry(_folder("demo_a", CurationStatus.NOT_SCANNED)))
    resolver = _FakeResolver({})
    with pytest.raises(FolderPathNotConfiguredError):
        scan_folder(repo, resolver, "demo_a")
    assert repo.save_count == 0
    assert repo.load().get("demo_a").status is CurationStatus.NOT_SCANNED


def test_log_estruturado_scan_folder_sem_caminho_absoluto(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """scan_folder emite log estruturado sem caminho absoluto."""
    repo = _FakeRepository(_registry(_folder("demo_a", CurationStatus.NOT_SCANNED)))
    resolver = _FakeResolver({"demo_a": tmp_path})
    with caplog.at_level(logging.INFO):
        scan_folder(repo, resolver, "demo_a")
    assert caplog.records
    for record in caplog.records:
        assert str(tmp_path) not in record.message


# --- US2: scan_all_folders (lote) ---------------------------------------------------


def test_lote_com_pastas_validas_e_invalidas_isola_falha(tmp_path: Path) -> None:
    """Lote de 200 pastas com 10 caminhos inválidos: as 190 são atualizadas, 10 falham (SC-002)."""
    folders = [_folder(f"pasta{i:03d}", CurationStatus.NOT_SCANNED) for i in range(200)]
    repo = _FakeRepository(_registry(*folders))
    paths = {f.alias.value: tmp_path for f in folders}
    broken = {
        f"pasta{i:03d}": FolderPathInvalidError(f"pasta{i:03d}", reason="caminho inexistente")
        for i in range(190, 200)
    }
    for alias in broken:
        del paths[alias]
    resolver = _FakeResolver(paths, broken=broken)
    report = scan_all_folders(repo, resolver)
    assert len(report.ok) == 190
    assert len(report.failures) == 10
    assert {f.alias for f in report.failures} == set(broken)


def test_registro_vazio_eh_ok() -> None:
    """Registro vazio produz relatório vazio, sem falhas (checklist CHK001)."""
    repo = _FakeRepository(_registry())
    resolver = _FakeResolver({})
    report = scan_all_folders(repo, resolver)
    assert report.ok == []
    assert report.failures == []
    assert report.duplicates == []


def test_todas_as_pastas_falham_nao_levanta(tmp_path: Path) -> None:
    """Todas as pastas do lote falhando não levanta exceção (checklist CHK002)."""
    folders = [
        _folder("demo_a", CurationStatus.NOT_SCANNED),
        _folder("demo_b", CurationStatus.NOT_SCANNED),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({})
    report = scan_all_folders(repo, resolver)
    assert report.ok == []
    assert len(report.failures) == 2


def test_relatorio_ordenado_por_alias(tmp_path: Path) -> None:
    """ok e failures são ordenados por alias (determinismo, checklist CHK020)."""
    folders = [
        _folder("zebra", CurationStatus.NOT_SCANNED),
        _folder("abelha", CurationStatus.NOT_SCANNED),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"zebra": tmp_path, "abelha": tmp_path})
    report = scan_all_folders(repo, resolver)
    assert [r.alias for r in report.ok] == ["abelha", "zebra"]


# --- US3: detecção de aliases duplicados --------------------------------------------


def test_dois_aliases_mesmo_caminho_real_formam_grupo_duplicado(tmp_path: Path) -> None:
    """Dois aliases resolvendo para o mesmo caminho real formam um grupo duplicado."""
    folders = [
        _folder("demo_a", CurationStatus.NOT_SCANNED),
        _folder("demo_dup", CurationStatus.NOT_SCANNED),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"demo_a": tmp_path, "demo_dup": tmp_path})
    report = scan_all_folders(repo, resolver)
    assert len(report.duplicates) == 1
    assert report.duplicates[0].aliases == ("demo_a", "demo_dup")
    # ambos continuam sendo varridos com sucesso, apesar da duplicidade
    assert {r.alias for r in report.ok} == {"demo_a", "demo_dup"}


def test_tres_aliases_mesmo_caminho_formam_um_unico_grupo(tmp_path: Path) -> None:
    """3+ aliases duplicados formam 1 grupo com os 3, não 3 pares (checklist CHK003)."""
    folders = [
        _folder("a1", CurationStatus.NOT_SCANNED),
        _folder("a2", CurationStatus.NOT_SCANNED),
        _folder("a3", CurationStatus.NOT_SCANNED),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"a1": tmp_path, "a2": tmp_path, "a3": tmp_path})
    report = scan_all_folders(repo, resolver)
    assert len(report.duplicates) == 1
    assert report.duplicates[0].aliases == ("a1", "a2", "a3")


def test_grupo_duplicado_nao_carrega_caminho_absoluto(tmp_path: Path) -> None:
    """DuplicateAliasGroup nunca carrega o caminho, nem no repr (checklist CHK019, FR-010)."""
    folders = [
        _folder("demo_a", CurationStatus.NOT_SCANNED),
        _folder("demo_dup", CurationStatus.NOT_SCANNED),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"demo_a": tmp_path, "demo_dup": tmp_path})
    report = scan_all_folders(repo, resolver)
    grupo = report.duplicates[0]
    assert not hasattr(grupo, "path")
    assert str(tmp_path) not in repr(grupo)


def test_alias_com_falha_nao_entra_na_comparacao_de_duplicidade(tmp_path: Path) -> None:
    """Alias que falha ao resolver não entra na comparação de duplicidade (checklist CHK015)."""
    folders = [
        _folder("demo_a", CurationStatus.NOT_SCANNED),
        _folder("demo_quebrada", CurationStatus.NOT_SCANNED),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"demo_a": tmp_path})
    report = scan_all_folders(repo, resolver)
    assert report.duplicates == []
    assert len(report.failures) == 1


def test_caminhos_distintos_nao_geram_duplicidade(tmp_path: Path) -> None:
    """Aliases com caminhos reais distintos não geram nenhum grupo duplicado."""
    outro = tmp_path / "outra"
    outro.mkdir()
    folders = [
        _folder("demo_a", CurationStatus.NOT_SCANNED),
        _folder("demo_b", CurationStatus.NOT_SCANNED),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"demo_a": tmp_path, "demo_b": outro})
    report = scan_all_folders(repo, resolver)
    assert report.duplicates == []
