# -*- coding: utf-8 -*-
"""
NOME: test_bootstrap_folders.py
TITULO: Testes de falha — caso de uso bootstrap_folders (fakes)
DATA: 22/09/2026 17:55
MODIFICADO: 23/09/2026 16:58
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.bootstrap_folders
HISTÓRICO:
    - 22/09/2026 17:55: criação (T013)
    - 22/09/2026 18:45: +casos de idempotência (T021, US2)
    - 23/09/2026 16:58: alias <raiz>__<sub>, idempotência por caminho (T028, feature 005)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.application.bootstrap_folders import BootstrapReport
from praxisforge.application.bootstrap_folders import bootstrap_folders as _bootstrap_folders
from praxisforge.application.ports import FolderLocator, FolderRegistryRepository, RootFolderProbe
from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import FolderPathUnreadableError
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry


class _FakeRepository(FolderRegistryRepository):
    def __init__(self, registry: FolderRegistry | None = None, exists: bool = True) -> None:
        self._registry = registry or FolderRegistry(schema_version="2", folders={})
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


class _FakeLocator(FolderLocator):
    """Canoniza resolvendo links; recusa os caminhos marcados como ilegíveis."""

    def __init__(self, ilegiveis: set[str] | None = None) -> None:
        self._ilegiveis = ilegiveis or set()

    def canonicalize(self, alias: str, raw: str) -> Path:
        if Path(raw).name in self._ilegiveis:
            raise FolderPathUnreadableError(alias)
        return Path(raw).resolve()

    def check(self, alias: str, path: Path) -> Path:  # pragma: no cover - não usado aqui
        return path


def bootstrap_folders(
    repo: FolderRegistryRepository, probe: RootFolderProbe, root: Path
) -> BootstrapReport:
    return _bootstrap_folders(repo, probe, root, locator=_FakeLocator())


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    pasta = tmp_path / "forks"
    pasta.mkdir()
    return pasta


def _paths(root: Path, *names: str) -> list[Path]:
    resultado = []
    for name in names:
        p = root / name
        p.mkdir(exist_ok=True)
        resultado.append(p)
    return resultado


def _existente(alias: str, caminho: Path, status: CurationStatus, **extra: object) -> Folder:
    campos: dict[str, object] = {
        "alias": Alias(alias),
        "description": "Já registrada",
        "content_type": "documents",
        "license": "unknown" if status is CurationStatus.IGNORE else "MIT",
        "last_scanned": None,
        "status": status,
        "path": str(caminho.resolve()),
    }
    campos.update(extra)
    return Folder(**campos)  # type: ignore[arg-type]


# --- US1 da feature 003 (adaptado) -----------------------------------------------------


def test_subpasta_com_readme_e_license_reconhecivel(raiz: Path) -> None:
    """Subpasta com README+LICENSE MIT é registrada not_scanned com alias <raiz>__<sub>."""
    subpastas = _paths(raiz, "repo_a")
    repo = _FakeRepository()
    probe = _FakeProbe(
        subpastas, descriptions={"repo_a": "Descrição do repo A"}, licenses={"repo_a": "MIT"}
    )
    report = bootstrap_folders(repo, probe, raiz)
    assert report.registered == ["forks__repo_a"]
    folder = repo.load().get("forks__repo_a")
    assert folder.license == "MIT"
    assert folder.status is CurationStatus.NOT_SCANNED
    assert folder.description == "Descrição do repo A"
    assert folder.path == str(subpastas[0].resolve())


def test_subpasta_com_readme_sem_license(raiz: Path) -> None:
    """Sem LICENSE reconhecível → unknown/pending."""
    repo = _FakeRepository()
    probe = _FakeProbe(_paths(raiz, "repo_b"), descriptions={"repo_b": "Descrição do repo B"})
    bootstrap_folders(repo, probe, raiz)
    folder = repo.load().get("forks__repo_b")
    assert folder.license == "unknown"
    assert folder.status is CurationStatus.PENDING


def test_subpasta_sem_readme_nem_license(raiz: Path) -> None:
    """Sem README nem LICENSE → descrição padrão."""
    repo = _FakeRepository()
    bootstrap_folders(repo, _FakeProbe(_paths(raiz, "repo_c")), raiz)
    assert repo.load().get("forks__repo_c").description


def test_raiz_sem_subpastas_nao_levanta(raiz: Path) -> None:
    """Pasta-raiz sem subpastas conclui sem erro."""
    report = bootstrap_folders(_FakeRepository(), _FakeProbe([]), raiz)
    assert report.registered == []
    assert report.failures == []


def test_escala_50_subpastas_40_reconheciveis_10_nao(raiz: Path) -> None:
    """50 subpastas registradas sem interromper (SC-003 da 003)."""
    nomes = [f"pasta{i:03d}" for i in range(50)]
    subpastas = _paths(raiz, *nomes)
    repo = _FakeRepository()
    probe = _FakeProbe(subpastas, licenses={nome: "MIT" for nome in nomes[:40]})
    report = bootstrap_folders(repo, probe, raiz)
    assert len(report.registered) == 50
    assert report.failures == []


def test_bootstrap_nunca_atribui_status_ignore(raiz: Path) -> None:
    """Nenhuma pasta registrada pelo bootstrap recebe status ignore."""
    repo = _FakeRepository()
    bootstrap_folders(repo, _FakeProbe(_paths(raiz, "repo_a", "repo_b")), raiz)
    assert all(f.status is not CurationStatus.IGNORE for f in repo.load().list())


# --- US2 da feature 005: aliases sem colisão --------------------------------------------


def test_duas_subpastas_que_normalizam_igual_recebem_sufixo(raiz: Path) -> None:
    """'Meu-Repo' e 'meu_repo' → forks__meu_repo e forks__meu_repo_2 (FR-007)."""
    repo = _FakeRepository()
    report = bootstrap_folders(repo, _FakeProbe(_paths(raiz, "meu_repo", "Meu-Repo")), raiz)
    assert report.registered == ["forks__meu_repo", "forks__meu_repo_2"]
    assert repo.load().get("forks__meu_repo").path.endswith("/Meu-Repo")
    assert report.failures == []


def test_duas_raizes_de_nomes_diferentes_nao_colidem(tmp_path: Path) -> None:
    """r1/graphify e r2/graphify → r1__graphify e r2__graphify (US2 c.1, SC-001)."""
    repo = _FakeRepository()
    for nome in ("r1", "r2"):
        raiz = tmp_path / nome
        raiz.mkdir()
        bootstrap_folders(repo, _FakeProbe(_paths(raiz, "graphify")), raiz)
    assert sorted(repo.load().folders) == ["r1__graphify", "r2__graphify"]


def test_raizes_de_mesmo_nome_recebem_sufixo(tmp_path: Path) -> None:
    """/a/forks/graphify e /b/forks/graphify → forks__graphify e forks__graphify_2 (US2 c.6)."""
    repo = _FakeRepository()
    for pai in ("a", "b"):
        raiz = tmp_path / pai / "forks"
        raiz.mkdir(parents=True)
        bootstrap_folders(repo, _FakeProbe(_paths(raiz, "graphify")), raiz)
    registro = repo.load()
    assert sorted(registro.folders) == ["forks__graphify", "forks__graphify_2"]
    assert "/b/forks/" in registro.get("forks__graphify_2").path


def test_nome_iniciado_por_digito_recebe_prefixo_p(raiz: Path) -> None:
    """'9-invalido' vira forks__p9_invalido, sem falha (FR-007)."""
    report = bootstrap_folders(_FakeRepository(), _FakeProbe(_paths(raiz, "9-invalido")), raiz)
    assert report.registered == ["forks__p9_invalido"]
    assert report.failures == []


def test_nome_que_normaliza_vazio_recebe_prefixo_p(raiz: Path) -> None:
    """Nome só com caracteres removidos ('ção!') vira forks__p (FR-007)."""
    report = bootstrap_folders(_FakeRepository(), _FakeProbe(_paths(raiz, "!!!")), raiz)
    assert report.registered == ["forks__p"]


def test_alias_longo_truncado_preservando_raiz_e_sufixo(raiz: Path) -> None:
    """Alias > 63 é truncado na parte da subpasta, mantendo 'forks__' e o sufixo (clarify)."""
    longo = "a" * 80
    repo = _FakeRepository()
    report = bootstrap_folders(repo, _FakeProbe(_paths(raiz, longo, longo.upper() + "-")), raiz)
    primeiro, segundo = report.registered
    assert primeiro.startswith("forks__") and len(primeiro) == 63
    assert segundo.startswith("forks__") and segundo.endswith("_2") and len(segundo) == 63


def test_sufixo_de_dois_digitos_cabe_em_63(raiz: Path) -> None:
    """Com 10+ colisões, '_10' também cabe no limite de 63 caracteres."""
    nomes = ["x" * 70 + "-" * i for i in range(11)]
    report = bootstrap_folders(_FakeRepository(), _FakeProbe(_paths(raiz, *nomes)), raiz)
    assert len(report.registered) == 11
    assert all(len(alias) <= 63 for alias in report.registered)
    assert report.registered[-1].endswith("_11")


def test_ordem_alfabetica_define_quem_recebe_sufixo(raiz: Path) -> None:
    """A lista do probe fora de ordem não muda o resultado (determinismo, SC-005)."""
    subpastas = _paths(raiz, "b-x", "B_X")
    report = bootstrap_folders(_FakeRepository(), _FakeProbe(list(reversed(subpastas))), raiz)
    assert report.registered == ["forks__b_x", "forks__b_x_2"]


# --- idempotência por caminho -------------------------------------------------------------


def test_pasta_ja_registrada_pelo_caminho_nao_e_alterada(raiz: Path) -> None:
    """Existente pelo caminho (mesmo com alias antigo) é pulada e mantida (FR-006)."""
    (subpasta,) = _paths(raiz, "repo_a")
    original = _existente("repo_a", subpasta, CurationStatus.CURATED)
    repo = _FakeRepository(FolderRegistry(schema_version="2", folders={}).add(original))
    report = bootstrap_folders(repo, _FakeProbe([subpasta]), raiz)
    assert report.registered == []
    assert report.skipped_existing == ["repo_a"]
    assert repo.load().get("repo_a") == original


def test_pasta_ignore_e_pulada(raiz: Path) -> None:
    """Existente com status ignore → skipped_ignored."""
    (subpasta,) = _paths(raiz, "pasta_tecnica")
    original = _existente("pasta_tecnica", subpasta, CurationStatus.IGNORE)
    repo = _FakeRepository(FolderRegistry(schema_version="2", folders={}).add(original))
    report = bootstrap_folders(repo, _FakeProbe([subpasta]), raiz)
    assert report.skipped_ignored == ["pasta_tecnica"]


def test_resumo_com_registrada_existente_e_ignorada(raiz: Path) -> None:
    """1 nova + 1 existente + 1 ignore nos grupos certos."""
    nova, existente, ignorada = _paths(raiz, "nova", "existente", "ignorada")
    registry = (
        FolderRegistry(schema_version="2", folders={})
        .add(_existente("existente", existente, CurationStatus.CURATED))
        .add(_existente("ignorada", ignorada, CurationStatus.IGNORE))
    )
    report = bootstrap_folders(
        _FakeRepository(registry), _FakeProbe([nova, existente, ignorada]), raiz
    )
    assert report.registered == ["forks__nova"]
    assert report.skipped_existing == ["existente"]
    assert report.skipped_ignored == ["ignorada"]


def test_alias_livre_mas_ocupado_por_outro_caminho_recebe_sufixo(
    raiz: Path, tmp_path: Path
) -> None:
    """forks__repo já usado por outro caminho → forks__repo_2 (nunca sobrescreve)."""
    outra = tmp_path / "outra"
    outra.mkdir()
    registry = FolderRegistry(schema_version="2", folders={}).add(
        _existente("forks__repo", outra, CurationStatus.CURATED)
    )
    repo = _FakeRepository(registry)
    report = bootstrap_folders(repo, _FakeProbe(_paths(raiz, "repo")), raiz)
    assert report.registered == ["forks__repo_2"]
    assert repo.load().get("forks__repo").path == str(outra.resolve())


def test_subpasta_movida_e_corrigida_e_reconhecida_pelo_novo_caminho(raiz: Path) -> None:
    """Após update --path, o bootstrap reconhece a pasta pelo caminho novo (SC-005)."""
    (subpasta,) = _paths(raiz, "repo_a")
    registry = FolderRegistry(schema_version="2", folders={}).add(
        _existente("nome_antigo", subpasta, CurationStatus.SCANNED)
    )
    repo = _FakeRepository(registry)
    report = bootstrap_folders(repo, _FakeProbe([subpasta]), raiz)
    assert report.skipped_existing == ["nome_antigo"]
    assert repo.save_count == 0


def test_raiz_nao_e_registrada(raiz: Path) -> None:
    """Só as subpastas são registradas, nunca a própria raiz (FR-017)."""
    repo = _FakeRepository()
    bootstrap_folders(repo, _FakeProbe(_paths(raiz, "repo_a")), raiz)
    assert repo.load().find_by_path(str(raiz.resolve())) is None


def test_subpasta_dentro_de_pasta_registrada_vira_falha(raiz: Path) -> None:
    """Raiz registrada como pasta → subpastas falham por aninhamento, sem interromper."""
    registry = FolderRegistry(schema_version="2", folders={}).add(
        _existente("github_forks", raiz, CurationStatus.PENDING, license="unknown")
    )
    report = bootstrap_folders(
        _FakeRepository(registry), _FakeProbe(_paths(raiz, "repo_a", "repo_b")), raiz
    )
    assert report.registered == []
    assert [f.error_type for f in report.failures] == ["NestedFolderPathError"] * 2


def test_subpasta_ilegivel_vira_falha_por_item(raiz: Path) -> None:
    """Locator recusa uma subpasta → falha por item; as demais seguem."""
    report = _bootstrap_folders(
        _FakeRepository(),
        _FakeProbe(_paths(raiz, "boa", "trancada")),
        raiz,
        locator=_FakeLocator(ilegiveis={"trancada"}),
    )
    assert report.registered == ["forks__boa"]
    assert [f.error_type for f in report.failures] == ["FolderPathUnreadableError"]


def test_registro_inexistente_e_tratado_como_vazio(raiz: Path) -> None:
    """Primeira execução sem folders.yaml prévio funciona."""
    report = bootstrap_folders(
        _FakeRepository(exists=False), _FakeProbe(_paths(raiz, "repo_a")), raiz
    )
    assert report.registered == ["forks__repo_a"]


def test_link_simbolico_gravado_pelo_destino(raiz: Path, tmp_path: Path) -> None:
    """Subpasta que é link é gravada pelo destino real (FR-002)."""
    destino = tmp_path / "destino_real"
    destino.mkdir()
    link = raiz / "atalho"
    link.symlink_to(destino)
    repo = _FakeRepository()
    bootstrap_folders(repo, _FakeProbe([link]), raiz)
    assert repo.load().get("forks__atalho").path == str(destino.resolve())
