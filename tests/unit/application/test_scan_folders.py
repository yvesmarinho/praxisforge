# -*- coding: utf-8 -*-
"""
NOME: test_scan_folders.py
TITULO: Testes de falha — casos de uso scan_folder e scan_all_folders (fakes)
DATA: 22/09/2026 12:35
MODIFICADO: 23/09/2026 16:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.scan_folders
HISTÓRICO:
    - 22/09/2026 12:35: criação (T002/T008/T014)
    - 22/09/2026 19:05: +caso pular status ignore no lote (T028, feature 003-bootstrap)
    - 23/09/2026 12:14: verificação de conteúdo e reversão (T024, T025, T031, feature 004)
    - 23/09/2026 16:52: FolderLocator no lugar de PathResolver (T021, feature 005)
STATUS: DEV
"""

import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from praxisforge.application.ports import (
    FolderLocator,
    FolderRegistryRepository,
    GitContentInspector,
)
from praxisforge.application.scan_folders import (
    ContentCheck,
    ScanBatchReport,
    ScanResult,
)
from praxisforge.application.scan_folders import scan_all_folders as _scan_all_folders
from praxisforge.application.scan_folders import scan_folder as _scan_folder
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    ContentInspectionError,
    FolderNotFoundError,
    FolderPathInvalidError,
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
    def __init__(
        self, paths: dict[str, Path], broken: Mapping[str, Exception] | None = None
    ) -> None:
        self._paths = paths
        self._broken = broken or {}

    def check(self, alias: str, path: Path) -> Path:
        if alias in self._broken:
            raise self._broken[alias]
        if alias not in self._paths:
            raise FolderPathInvalidError(alias, "pasta não encontrada no caminho registrado")
        return self._paths[alias]

    def canonicalize(self, alias: str, raw: str) -> Path:  # pragma: no cover - não usado aqui
        return Path(raw)


class _FakeInspector(GitContentInspector):
    """Inspector programável: HEAD por caminho, mudança por (caminho, hash), erros por caminho."""

    def __init__(
        self,
        heads: Mapping[Path, str | None] | None = None,
        changed: Mapping[tuple[Path, str], bool] | None = None,
        errors: Mapping[Path, Exception] | None = None,
    ) -> None:
        self._heads = heads or {}
        self._changed = changed or {}
        self._errors = errors or {}
        self.calls: list[tuple[str, Path]] = []

    def head_commit(self, path: Path) -> str | None:
        self.calls.append(("head_commit", path))
        if path in self._errors:
            raise self._errors[path]
        return self._heads.get(path)

    def changed_since(self, path: Path, commit: str) -> bool:
        self.calls.append(("changed_since", path))
        if path in self._errors:
            raise self._errors[path]
        return self._changed.get((path, commit), False)


def scan_folder(
    repository: FolderRegistryRepository, resolver: FolderLocator, alias: str
) -> ScanResult:
    """Casos das features 002/003: pastas fora de repositório git (inspector devolve None)."""
    return _scan_folder(repository, resolver, alias, inspector=_FakeInspector())


def scan_all_folders(
    repository: FolderRegistryRepository, resolver: FolderLocator
) -> ScanBatchReport:
    """Casos das features 002/003: pastas fora de repositório git (inspector devolve None)."""
    return _scan_all_folders(repository, resolver, inspector=_FakeInspector())


def _folder(
    alias: str,
    status: CurationStatus,
    license: str = "MIT",  # noqa: A002
    commit: str | None = None,
) -> Folder:
    return Folder(
        alias=Alias(alias),
        description=f"Descrição de {alias}",
        content_type="documents",
        license=license,
        last_scanned=None,
        status=status,
        path=f"/srv/pastas/{alias}",
        last_curated_commit=commit,
    )


def _registry(*folders: Folder) -> FolderRegistry:
    reg = FolderRegistry(schema_version="2", folders={})
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
    repo = _FakeRepository(_registry(_folder("demo_a", CurationStatus.PENDING, license="unknown")))
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
    with pytest.raises(FolderPathInvalidError):
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


# --- pastas com status ignore (feature 003) -------------------------------------------


def test_lote_pula_pasta_com_status_ignore(tmp_path: Path) -> None:
    """scan_all_folders pula pasta ignore: não resolve caminho, não conta ok/failures."""
    folders = [
        _folder("demo_a", CurationStatus.NOT_SCANNED),
        _folder("pasta_ignorada", CurationStatus.IGNORE, license="unknown"),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"demo_a": tmp_path})  # sem entrada para pasta_ignorada
    report = scan_all_folders(repo, resolver)
    assert [r.alias for r in report.ok] == ["demo_a"]
    assert report.failures == []
    assert report.ignored == ["pasta_ignorada"]


def test_lote_ignora_apenas_pasta_ignore_demais_normais(tmp_path: Path) -> None:
    """Demais pastas continuam processadas normalmente quando há uma pasta ignore no meio."""
    folders = [
        _folder("demo_a", CurationStatus.NOT_SCANNED),
        _folder("demo_b", CurationStatus.NOT_SCANNED),
        _folder("pasta_ignorada", CurationStatus.IGNORE, license="unknown"),
    ]
    repo = _FakeRepository(_registry(*folders))
    resolver = _FakeResolver({"demo_a": tmp_path, "demo_b": tmp_path})
    report = scan_all_folders(repo, resolver)
    assert {r.alias for r in report.ok} == {"demo_a", "demo_b"}
    assert report.ignored == ["pasta_ignorada"]


# --- feature 004 / US2: verificação de conteúdo --------------------------------------

_GRAVADO = "a" * 40
_HEAD = "b" * 40


def test_curada_alterada_e_revertida(tmp_path: Path) -> None:
    """Curada com conteúdo alterado → in_curation, REVERTED, hash mantido (FR-005)."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED, commit=_GRAVADO)))
    inspector = _FakeInspector(heads={tmp_path: _HEAD}, changed={(tmp_path, _GRAVADO): True})
    resultado = _scan_folder(repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=inspector)
    assert resultado.content_check is ContentCheck.REVERTED
    assert resultado.status is CurationStatus.IN_CURATION
    folder = repo.load().get("fonte")
    assert folder.status is CurationStatus.IN_CURATION
    assert folder.last_curated_commit == _GRAVADO
    assert folder.last_scanned == resultado.last_scanned


def test_curada_inalterada_continua_curada(tmp_path: Path) -> None:
    """Curada sem mudança na pasta → curated, UNCHANGED, só last_scanned avança (FR-006)."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED, commit=_GRAVADO)))
    inspector = _FakeInspector(heads={tmp_path: _HEAD}, changed={(tmp_path, _GRAVADO): False})
    resultado = _scan_folder(repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=inspector)
    assert resultado.content_check is ContentCheck.UNCHANGED
    folder = repo.load().get("fonte")
    assert folder.status is CurationStatus.CURATED
    assert folder.last_curated_commit == _GRAVADO
    assert folder.last_scanned is not None


def test_curada_que_deixou_de_ser_git_nao_reverte(tmp_path: Path) -> None:
    """Curada com hash, mas pasta não é mais git → NOT_GIT, status mantido."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED, commit=_GRAVADO)))
    inspector = _FakeInspector(heads={tmp_path: None})
    resultado = _scan_folder(repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=inspector)
    assert resultado.content_check is ContentCheck.NOT_GIT
    assert repo.load().get("fonte").status is CurationStatus.CURATED
    assert ("changed_since", tmp_path) not in inspector.calls


@pytest.mark.parametrize(
    "status",
    [
        CurationStatus.SCANNED,
        CurationStatus.IN_CURATION,
        CurationStatus.PENDING,
        CurationStatus.IGNORE,
    ],
)
def test_status_diferente_de_curada_nao_consulta_git(
    tmp_path: Path, status: CurationStatus
) -> None:
    """Hash remanescente em outro status não dispara verificação (FR-007, FR-015)."""
    license = "unknown" if status is CurationStatus.PENDING else "MIT"  # noqa: A001
    repo = _FakeRepository(_registry(_folder("fonte", status, license=license, commit=_GRAVADO)))
    inspector = _FakeInspector(heads={tmp_path: _HEAD}, changed={(tmp_path, _GRAVADO): True})
    resultado = _scan_folder(repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=inspector)
    assert resultado.content_check is ContentCheck.NOT_APPLICABLE
    assert resultado.status is status
    assert inspector.calls == []


def test_falha_do_git_no_individual_nao_persiste_nada(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """ContentInspectionError → propagada com alias; status/hash/last_scanned intactos (FR-009)."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED, commit=_GRAVADO)))
    inspector = _FakeInspector(errors={tmp_path: ContentInspectionError("", "tempo esgotado")})
    with pytest.raises(ContentInspectionError) as info:
        _scan_folder(repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=inspector)
    assert info.value.alias == "fonte"
    assert repo.save_count == 0
    folder = repo.load().get("fonte")
    assert folder.last_scanned is None
    assert folder.status is CurationStatus.CURATED


def test_reversao_emite_log_estruturado_sem_caminho(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Evento content_check com outcome=reverted, sem caminho absoluto (C2 do analyze)."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED, commit=_GRAVADO)))
    inspector = _FakeInspector(heads={tmp_path: _HEAD}, changed={(tmp_path, _GRAVADO): True})
    with caplog.at_level(logging.INFO):
        _scan_folder(repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=inspector)
    mensagens = [record.getMessage() for record in caplog.records]
    assert any('"content_check"' in m and '"reverted"' in m for m in mensagens)
    assert all(str(tmp_path) not in m for m in mensagens)


def test_lote_misto_so_reverte_curada_alterada(tmp_path: Path) -> None:
    """Lote: só a curada alterada reverte; ignore pulada; falha por item isolada (FR-008/009)."""
    caminhos = {
        nome: tmp_path / nome
        for nome in ("alterada", "inalterada", "nao_git", "quebrada", "varrida")
    }
    repo = _FakeRepository(
        _registry(
            _folder("alterada", CurationStatus.CURATED, commit=_GRAVADO),
            _folder("inalterada", CurationStatus.CURATED, commit=_GRAVADO),
            _folder("nao_git", CurationStatus.CURATED, commit=_GRAVADO),
            _folder("quebrada", CurationStatus.CURATED, commit=_GRAVADO),
            _folder("varrida", CurationStatus.SCANNED, commit=_GRAVADO),
            _folder("ignorada", CurationStatus.IGNORE),
        )
    )
    inspector = _FakeInspector(
        heads={
            caminhos["alterada"]: _HEAD,
            caminhos["inalterada"]: _HEAD,
            caminhos["nao_git"]: None,
        },
        changed={(caminhos["alterada"], _GRAVADO): True},
        errors={caminhos["quebrada"]: ContentInspectionError("", "tempo esgotado")},
    )
    report = _scan_all_folders(repo, _FakeResolver(caminhos), inspector=inspector)

    por_alias = {r.alias: r for r in report.ok}
    assert set(por_alias) == {"alterada", "inalterada", "nao_git", "varrida"}
    assert por_alias["alterada"].content_check is ContentCheck.REVERTED
    assert por_alias["inalterada"].content_check is ContentCheck.UNCHANGED
    assert por_alias["nao_git"].content_check is ContentCheck.NOT_GIT
    assert por_alias["varrida"].content_check is ContentCheck.NOT_APPLICABLE
    assert report.ignored == ["ignorada"]
    assert [(f.alias, f.error_type) for f in report.failures] == [
        ("quebrada", "ContentInspectionError")
    ]
    registro = repo.load()
    assert registro.get("alterada").status is CurationStatus.IN_CURATION
    assert registro.get("inalterada").status is CurationStatus.CURATED
    assert registro.get("quebrada").status is CurationStatus.CURATED
    assert registro.get("quebrada").last_scanned is None
    assert registro.get("varrida").status is CurationStatus.SCANNED


def test_lote_dois_aliases_no_mesmo_repositorio_com_hashes_diferentes(tmp_path: Path) -> None:
    """Cada alias compara com o próprio hash: só o de hash antigo reverte (E1 do analyze)."""
    antigo, atual = "c" * 40, "d" * 40
    repo = _FakeRepository(
        _registry(
            _folder("fonte_a", CurationStatus.CURATED, commit=antigo),
            _folder("fonte_b", CurationStatus.CURATED, commit=atual),
        )
    )
    inspector = _FakeInspector(
        heads={tmp_path: atual},
        changed={(tmp_path, antigo): True, (tmp_path, atual): False},
    )
    report = _scan_all_folders(
        repo, _FakeResolver({"fonte_a": tmp_path, "fonte_b": tmp_path}), inspector=inspector
    )
    por_alias = {r.alias: r.content_check for r in report.ok}
    assert por_alias == {"fonte_a": ContentCheck.REVERTED, "fonte_b": ContentCheck.UNCHANGED}
    assert report.reverted == ["fonte_a"]


# --- feature 004 / US3: legado curado sem versão gravada ------------------------------


def test_legado_git_sem_hash_recebe_baseline(tmp_path: Path) -> None:
    """Curada sem hash + git → grava o HEAD, BASELINE_RECORDED, continua curada (FR-014)."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED)))
    inspector = _FakeInspector(heads={tmp_path: _HEAD})
    resultado = _scan_folder(repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=inspector)
    assert resultado.content_check is ContentCheck.BASELINE_RECORDED
    folder = repo.load().get("fonte")
    assert folder.status is CurationStatus.CURATED
    assert folder.last_curated_commit == _HEAD
    assert ("changed_since", tmp_path) not in inspector.calls
    assert repo.save_count == 1


def test_legado_nao_git_sem_hash_nada_gravado(tmp_path: Path) -> None:
    """Curada sem hash + não-git → NOT_GIT e nenhuma versão gravada."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED)))
    resultado = _scan_folder(
        repo, _FakeResolver({"fonte": tmp_path}), "fonte", inspector=_FakeInspector()
    )
    assert resultado.content_check is ContentCheck.NOT_GIT
    assert repo.load().get("fonte").last_curated_commit is None


def test_legado_segunda_varredura_apos_mudanca_reverte(tmp_path: Path) -> None:
    """Baseline gravada numa varredura; mudança depois → próxima varredura reverte (US3 c.2)."""
    repo = _FakeRepository(_registry(_folder("fonte", CurationStatus.CURATED)))
    resolver = _FakeResolver({"fonte": tmp_path})
    _scan_folder(repo, resolver, "fonte", inspector=_FakeInspector(heads={tmp_path: _HEAD}))
    depois = _FakeInspector(heads={tmp_path: "e" * 40}, changed={(tmp_path, _HEAD): True})
    resultado = _scan_folder(repo, resolver, "fonte", inspector=depois)
    assert resultado.content_check is ContentCheck.REVERTED
    assert repo.load().get("fonte").status is CurationStatus.IN_CURATION
