# -*- coding: utf-8 -*-
"""
NOME: test_folder_registry.py
TITULO: Testes de falha — agregado FolderRegistry
DATA: 22/09/2026 09:45
MODIFICADO: 23/09/2026 16:47
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.folder_registry
HISTÓRICO:
    - 22/09/2026 09:45: criação (T009)
    - 23/09/2026 12:04: +update(last_curated_commit) (T005, feature 004)
    - 23/09/2026 16:47: unicidade/aninhamento de path (T005, feature 005)
STATUS: DEV
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from praxisforge.domain.alias import Alias
from praxisforge.domain.curation_status import CurationStatus
from praxisforge.domain.errors import (
    AliasAlreadyRegisteredError,
    FolderNotFoundError,
    InvalidCommitHashError,
    NestedFolderPathError,
    PathAlreadyRegisteredError,
    UnsupportedSchemaVersionError,
)
from praxisforge.domain.folder import Folder
from praxisforge.domain.folder_registry import FolderRegistry


def _folder(alias: str = "github_forks", **overrides: object) -> Folder:
    fields: dict[str, object] = {
        "alias": Alias(alias),
        "description": "Forks de repositórios de referência",
        "content_type": "repository_forks",
        "license": "unknown",
        "last_scanned": None,
        "status": CurationStatus.PENDING,
        "path": f"/srv/pastas/{alias}",
    }
    fields.update(overrides)
    return Folder(**fields)  # type: ignore[arg-type]


def test_add_novo_alias() -> None:
    """add registra um alias novo no agregado."""
    registry = FolderRegistry(schema_version="2", folders={})
    updated = registry.add(_folder())
    assert updated.get("github_forks").alias.value == "github_forks"


def test_add_identico_eh_no_op() -> None:
    """add com os mesmos dados de um alias já registrado é idempotente (no-op)."""
    registry = FolderRegistry(schema_version="2", folders={})
    registry = registry.add(_folder())
    same = registry.add(_folder())
    assert same.get("github_forks") == registry.get("github_forks")


def test_add_com_dados_diferentes_levanta_erro_sem_alterar() -> None:
    """add com dados diferentes para um alias existente levanta erro e não altera o agregado."""
    registry = FolderRegistry(schema_version="2", folders={})
    registry = registry.add(_folder())
    with pytest.raises(AliasAlreadyRegisteredError):
        registry.add(_folder(description="Outra descrição"))
    assert registry.get("github_forks").description == "Forks de repositórios de referência"


def test_get_inexistente_levanta_erro() -> None:
    """get de alias inexistente levanta FolderNotFoundError."""
    registry = FolderRegistry(schema_version="2", folders={})
    with pytest.raises(FolderNotFoundError):
        registry.get("inexistente")


def test_update_atomico_de_status_last_scanned_licenca() -> None:
    """update aplica status, last_scanned e license em conjunto, atomicamente."""
    registry = FolderRegistry(schema_version="2", folders={})
    registry = registry.add(_folder())
    now = datetime(2026, 9, 21, 15, 55, tzinfo=ZoneInfo("America/Sao_Paulo"))
    updated = registry.update(
        "github_forks", status=CurationStatus.SCANNED, last_scanned=now, license="MIT"
    )
    folder = updated.get("github_forks")
    assert folder.status is CurationStatus.SCANNED
    assert folder.last_scanned == now
    assert folder.license == "MIT"


def test_update_com_mudanca_invalida_nao_altera_nada() -> None:
    """Uma mudança que violaria invariantes não altera o agregado (atômico)."""
    registry = FolderRegistry(schema_version="2", folders={})
    registry = registry.add(_folder())
    with pytest.raises(Exception):  # noqa: B017 - qualquer erro semântico do domínio
        registry.update("github_forks", status=CurationStatus.SCANNED)  # licença ainda unknown
    assert registry.get("github_forks").status is CurationStatus.PENDING


def test_update_alias_inexistente_levanta_erro() -> None:
    """update de alias inexistente levanta FolderNotFoundError."""
    registry = FolderRegistry(schema_version="2", folders={})
    with pytest.raises(FolderNotFoundError):
        registry.update("inexistente", status=CurationStatus.SCANNED)


@pytest.mark.parametrize("versao", ["1", "3"])
def test_schema_version_diferente_de_2_levanta_erro(versao: str) -> None:
    """Só a v2 é suportada no Domain; v1 só via migração (feature 005)."""
    with pytest.raises(UnsupportedSchemaVersionError):
        FolderRegistry(schema_version=versao, folders={})


def test_list_ordenado_por_alias() -> None:
    """list devolve as pastas ordenadas por alias."""
    registry = FolderRegistry(schema_version="2", folders={})
    registry = registry.add(_folder(alias="zebra"))
    registry = registry.add(_folder(alias="abelha"))
    aliases = [folder.alias.value for folder in registry.list()]
    assert aliases == ["abelha", "zebra"]


def _registry_curado(commit: str | None = "a" * 40) -> FolderRegistry:
    agora = datetime(2026, 9, 22, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    folder = _folder(
        license="MIT",
        status=CurationStatus.CURATED,
        last_scanned=agora,
        last_curated_commit=commit,
    )
    return FolderRegistry(schema_version="2", folders={}).add(folder)


def test_update_grava_last_curated_commit_quando_informado() -> None:
    """update aplica o hash informado."""
    updated = _registry_curado(None).update("github_forks", last_curated_commit="c" * 40)
    assert updated.get("github_forks").last_curated_commit == "c" * 40


def test_update_sem_hash_mantem_valor_atual() -> None:
    """Omitir o hash preserva o valor anterior."""
    updated = _registry_curado().update("github_forks", license="Apache-2.0")
    assert updated.get("github_forks").last_curated_commit == "a" * 40


def test_update_de_status_preserva_hash_como_historico() -> None:
    """Sair de curated sem informar hash mantém a versão gravada (FR-010)."""
    updated = _registry_curado().update("github_forks", status=CurationStatus.IN_CURATION)
    folder = updated.get("github_forks")
    assert folder.status is CurationStatus.IN_CURATION
    assert folder.last_curated_commit == "a" * 40


def test_update_com_hash_invalido_nao_altera_nada() -> None:
    """Atualização atômica: hash inválido não altera o agregado."""
    registry = _registry_curado()
    with pytest.raises(InvalidCommitHashError):
        registry.update(
            "github_forks", status=CurationStatus.IN_CURATION, last_curated_commit="xyz"
        )
    assert registry.get("github_forks").status is CurationStatus.CURATED
    assert registry.get("github_forks").last_curated_commit == "a" * 40


# --- feature 005: unicidade e aninhamento de path --------------------------------------


def _com(*folders: Folder) -> FolderRegistry:
    registry = FolderRegistry(schema_version="2", folders={})
    for folder in folders:
        registry = registry.add(folder)
    return registry


@pytest.mark.parametrize(
    "outro", ["/srv/forks/repo", "/SRV/Forks/Repo"], ids=["igual", "maiusculas"]
)
def test_add_com_path_duplicado_levanta_erro_citando_dono(outro: str) -> None:
    """Mesmo caminho (ignorando maiúsculas) → PathAlreadyRegisteredError(owner) (FR-003)."""
    registry = _com(_folder("repo_a", path="/srv/forks/repo"))
    with pytest.raises(PathAlreadyRegisteredError) as info:
        registry.add(_folder("repo_b", path=outro))
    assert info.value.owner == "repo_a"


@pytest.mark.parametrize(
    ("existente", "novo"),
    [("/srv/forks", "/srv/forks/repo"), ("/srv/forks/repo", "/srv/forks"), ("/", "/srv")],
    ids=["descendente", "ancestral", "raiz_do_sistema"],
)
def test_add_aninhado_levanta_erro(existente: str, novo: str) -> None:
    """Nenhuma pasta dentro de outra (FR-003, Clarificação CHK005)."""
    registry = _com(_folder("existente", path=existente))
    with pytest.raises(NestedFolderPathError) as info:
        registry.add(_folder("nova", path=novo))
    assert info.value.owner == "existente"


def test_prefixo_de_nome_nao_eh_aninhamento() -> None:
    """/srv/forks e /srv/forks2 são irmãs, não aninhadas."""
    registry = _com(_folder("pasta_a", path="/srv/forks"))
    assert "pasta_b" in registry.add(_folder("pasta_b", path="/srv/forks2")).folders


def test_update_path_preserva_demais_campos_e_revalida() -> None:
    """update(path=) atômico; duplicado → erro sem alterar nada (FR-016)."""
    registry = _com(
        _folder(
            "pasta_a",
            path="/srv/a",
            license="MIT",
            status=CurationStatus.SCANNED,
            last_scanned=datetime(2026, 9, 1, tzinfo=ZoneInfo("America/Sao_Paulo")),
        ),
        _folder("pasta_b", path="/srv/b"),
    )
    movida = registry.update("pasta_a", path="/srv/nova_a")
    assert movida.get("pasta_a").path == "/srv/nova_a"
    assert movida.get("pasta_a").status is CurationStatus.SCANNED
    assert movida.get("pasta_a").license == "MIT"
    with pytest.raises(PathAlreadyRegisteredError):
        registry.update("pasta_a", path="/srv/b")
    assert registry.get("pasta_a").path == "/srv/a"


def test_update_para_o_proprio_path_nao_eh_duplicidade() -> None:
    """Revalidação ignora a própria pasta."""
    registry = _com(_folder("pasta_a", path="/srv/a"))
    assert registry.update("pasta_a", path="/SRV/A").get("pasta_a").path == "/SRV/A"


def test_find_by_path_ignora_maiusculas() -> None:
    """find_by_path compara com casefold e devolve None quando ausente."""
    registry = _com(_folder("pasta_a", path="/srv/Forks/A"))
    encontrada = registry.find_by_path("/srv/forks/a")
    assert encontrada is not None and encontrada.alias.value == "pasta_a"
    assert registry.find_by_path("/srv/outra") is None


def test_construir_registro_com_paths_duplicados_levanta_erro() -> None:
    """Invariante também vale ao reconstruir (YAML editado à mão) — SC-004."""
    a = _folder("pasta_a", path="/srv/x")
    b = _folder("pasta_b", path="/srv/x")
    with pytest.raises(PathAlreadyRegisteredError):
        FolderRegistry(schema_version="2", folders={"pasta_a": a, "pasta_b": b})
