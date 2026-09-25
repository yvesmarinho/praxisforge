# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_library_repository.py
TITULO: Testes de integração — FilesystemLibraryRepository (leitura de library/, hash)
DATA: 25/09/2026 13:02
MODIFICADO: 25/09/2026 13:02
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_library_repository
HISTÓRICO:
    - 25/09/2026 13:02: criação (T013, feature 009) — sucede test_filesystem_skill_repository.py
STATUS: DEV
"""

import shutil
from pathlib import Path

import pytest

from praxisforge.domain.errors import (
    InvalidLibraryItemError,
    LibraryItemNotFoundError,
    LibraryNotFoundError,
)
from praxisforge.domain.library_item import ItemKind
from praxisforge.infrastructure.filesystem_library_repository import FilesystemLibraryRepository
from tests.library_helpers import criar_projeto, escrever_item


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return criar_projeto(tmp_path / "projeto")


def _repo(root: Path) -> FilesystemLibraryRepository:
    return FilesystemLibraryRepository(root / "library")


def test_list_entries_pasta_e_arquivo(root: Path) -> None:
    """Tipos de pasta listam pastas; de arquivo, .md sem extensão; ignora _ e .; ordena."""
    escrever_item(root, "skill", "zeta")
    escrever_item(root, "skill", "alfa")
    (root / "library" / "skills" / "_rascunho").mkdir()
    (root / "library" / "skills" / "solto.md").write_text("x", encoding="utf-8")
    escrever_item(root, "command", "revisar")
    (root / "library" / "commands" / ".oculto.md").write_text("x", encoding="utf-8")
    (root / "library" / "commands" / "notas.txt").write_text("x", encoding="utf-8")
    repo = _repo(root)
    assert repo.list_entries(ItemKind.SKILL) == ["alfa", "zeta"]
    assert repo.list_entries(ItemKind.COMMAND) == ["revisar"]
    assert repo.list_entries(ItemKind.AGENT) == []


def test_unknown_entries(root: Path) -> None:
    """Diretório fora dos tipos e arquivo solto em pasta de tipo são desconhecidos."""
    (root / "library" / "prompts").mkdir()
    (root / "library" / "prompts" / "x.md").write_text("x", encoding="utf-8")
    (root / "library" / "skills" / "solto.md").write_text("x", encoding="utf-8")
    (root / "library" / "commands" / "pasta").mkdir()
    (root / "library" / "INDEX.md").write_text("x", encoding="utf-8")
    (root / "library" / "_templates").mkdir()
    assert _repo(root).unknown_entries() == ["commands/pasta", "prompts", "skills/solto.md"]


def test_library_ausente(tmp_path: Path) -> None:
    """Sem library/ → LibraryNotFoundError."""
    with pytest.raises(LibraryNotFoundError):
        FilesystemLibraryRepository(tmp_path / "library").list_entries(ItemKind.SKILL)


def test_load_skill_com_apoio(root: Path) -> None:
    """Skill: frontmatter, links do corpo e ausentes."""
    escrever_item(
        root,
        "skill",
        "alfa",
        corpo="[a](ref/a.md) [b](ref/b.md) [c](https://x.io)\n",
        arquivos={"ref/a.md": "a"},
    )
    doc = _repo(root).load(ItemKind.SKILL, "alfa")
    assert (doc.kind, doc.entry_name) == (ItemKind.SKILL, "alfa")
    assert doc.support_files == ["ref/a.md", "ref/b.md"]
    assert doc.missing_files == ["ref/b.md"]


def test_load_hook_run_ausente(root: Path) -> None:
    """Hook: arquivos do run que não existem vão para missing_files."""
    escrever_item(
        root,
        "hook",
        "aviso",
        campos={"event": "Stop", "run": ["a.sh", "b.sh"]},
        arquivos={"a.sh": "x"},
    )
    doc = _repo(root).load(ItemKind.HOOK, "aviso")
    assert doc.missing_files == ["b.sh"]


def test_load_command(root: Path) -> None:
    """Arquivo único: frontmatter e links locais citados."""
    escrever_item(root, "command", "revisar", corpo="Veja [x](apoio.md).\n")
    doc = _repo(root).load(ItemKind.COMMAND, "revisar")
    assert doc.frontmatter["description"] == "Descrição do item"
    assert doc.support_files == ["apoio.md"]


def test_load_inexistente(root: Path) -> None:
    """Item que não existe → LibraryItemNotFoundError."""
    with pytest.raises(LibraryItemNotFoundError):
        _repo(root).load(ItemKind.AGENT, "nada")


@pytest.mark.parametrize(
    ("conteudo", "trecho"),
    [
        ("sem frontmatter\n", "sem frontmatter"),
        ("---\nname: x\n", "não fechado"),
        ("---\n: [\n---\n", "corrompido"),
        ("---\n- a\n---\n", "não é um mapa"),
    ],
)
def test_load_frontmatter_invalido(root: Path, conteudo: str, trecho: str) -> None:
    """Frontmatter ausente, aberto, corrompido ou não-mapa → InvalidLibraryItemError."""
    (root / "library" / "rules" / "r.md").write_text(conteudo, encoding="utf-8")
    with pytest.raises(InvalidLibraryItemError) as erro:
        _repo(root).load(ItemKind.RULE, "r")
    assert trecho in str(erro.value)


def test_load_pasta_sem_arquivo_principal(root: Path) -> None:
    """Pasta de hook sem HOOK.md → InvalidLibraryItemError citando o arquivo."""
    (root / "library" / "hooks" / "h").mkdir()
    with pytest.raises(InvalidLibraryItemError) as erro:
        _repo(root).load(ItemKind.HOOK, "h")
    assert "HOOK.md" in str(erro.value)


def test_load_ilegivel(root: Path) -> None:
    """Arquivo ilegível (bytes inválidos) → InvalidLibraryItemError, não exceção crua."""
    (root / "library" / "agents" / "a.md").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(InvalidLibraryItemError) as erro:
        _repo(root).load(ItemKind.AGENT, "a")
    assert "ilegível" in str(erro.value)


def test_hash_estavel_ao_mover_pasta(root: Path, tmp_path: Path) -> None:
    """Hash usa caminhos relativos ao item: mover o acervo não muda o hash (FR-017)."""
    escrever_item(root, "skill", "alfa", arquivos={"ref/a.md": "a"})
    antes = _repo(root).content_hash(ItemKind.SKILL, "alfa")
    destino = tmp_path / "outro"
    shutil.copytree(root / "library", destino / "library")
    assert (
        FilesystemLibraryRepository(destino / "library").content_hash(ItemKind.SKILL, "alfa")
        == antes
    )


def test_hash_skill_igual_ao_da_008(root: Path) -> None:
    """O hash de skill é o mesmo algoritmo da 008 (publicações antigas continuam iguais)."""
    from praxisforge.infrastructure.filesystem_skill_repository import FilesystemSkillRepository

    escrever_item(root, "skill", "alfa", arquivos={"ref/a.md": "a"})
    (root / "library" / "skills" / "alfa" / ".praxisforge-skill.json").write_text(
        "{}", encoding="utf-8"
    )
    novo = _repo(root).content_hash(ItemKind.SKILL, "alfa")
    antigo = FilesystemSkillRepository(root / "library" / "skills").content_hash("alfa")
    assert novo == antigo


def test_hash_arquivo_unico_muda_com_conteudo(root: Path) -> None:
    """Hash de arquivo único muda quando o conteúdo muda."""
    arquivo = escrever_item(root, "command", "revisar")
    antes = _repo(root).content_hash(ItemKind.COMMAND, "revisar")
    arquivo.write_text(arquivo.read_text(encoding="utf-8") + "mais\n", encoding="utf-8")
    assert _repo(root).content_hash(ItemKind.COMMAND, "revisar") != antes


def test_item_path(root: Path) -> None:
    """item_path aponta para a pasta ou para o .md."""
    repo = _repo(root)
    assert repo.item_path(ItemKind.SKILL, "a") == root / "library" / "skills" / "a"
    assert repo.item_path(ItemKind.RULE, "r") == root / "library" / "rules" / "r.md"
