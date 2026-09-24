# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_skill_repository.py
TITULO: Testes de integração — FilesystemSkillRepository (leitura de skills/, hash)
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_skill_repository
HISTÓRICO:
    - 24/09/2026 16:54: criação (T012, feature 008)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.domain.errors import InvalidSkillError, SkillNotFoundError
from praxisforge.infrastructure.filesystem_skill_repository import FilesystemSkillRepository
from tests.skills_helpers import escrever_skill


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "skills").mkdir()
    return tmp_path


def test_list_names_ignora_template_ocultas_e_arquivos(root: Path) -> None:
    """Pastas iniciadas por _ ou . e arquivos soltos não são skills; ordem alfabética."""
    escrever_skill(root, "zeta")
    escrever_skill(root, "alfa")
    (root / "skills" / "_template").mkdir()
    (root / "skills" / ".oculta").mkdir()
    (root / "skills" / "README.md").write_text("x", encoding="utf-8")
    assert FilesystemSkillRepository(root / "skills").list_names() == ["alfa", "zeta"]


def test_list_names_sem_pasta_skills(tmp_path: Path) -> None:
    """Sem skills/ não há skills."""
    assert FilesystemSkillRepository(tmp_path / "skills").list_names() == []


def test_load_devolve_frontmatter_e_referencias(root: Path) -> None:
    """load lê frontmatter, referências do corpo e aponta as ausentes."""
    escrever_skill(
        root,
        "alfa",
        sources=["guia-a"],
        corpo="Veja [a](ref/a.md) e [b](ref/b.md) e [c](https://x.io).\n",
        arquivos={"ref/a.md": "a"},
    )
    documento = FilesystemSkillRepository(root / "skills").load("alfa")
    assert documento.folder_name == "alfa"
    assert documento.frontmatter["name"] == "alfa"
    assert documento.references == ["ref/a.md", "ref/b.md"]
    assert documento.missing_references == ["ref/b.md"]


def test_load_referencia_fora_da_pasta_nao_e_consultada(root: Path) -> None:
    """Referência que sai da pasta fica para a entidade, não é marcada como ausente."""
    escrever_skill(root, "alfa", corpo="[x](../fora.md)\n")
    documento = FilesystemSkillRepository(root / "skills").load("alfa")
    assert documento.references == ["../fora.md"]
    assert documento.missing_references == []


def test_load_skill_inexistente(root: Path) -> None:
    """Nome sem pasta → SkillNotFoundError."""
    with pytest.raises(SkillNotFoundError):
        FilesystemSkillRepository(root / "skills").load("nada")


def test_load_sem_skill_md(root: Path) -> None:
    """Pasta sem SKILL.md → InvalidSkillError."""
    (root / "skills" / "alfa").mkdir()
    with pytest.raises(InvalidSkillError) as info:
        FilesystemSkillRepository(root / "skills").load("alfa")
    assert "SKILL.md" in str(info.value)


@pytest.mark.parametrize(
    ("conteudo", "motivo"),
    [
        ("sem frontmatter\n", "sem frontmatter"),
        ("---\nname: alfa\n", "não fechado"),
        ("---\nname: [alfa\n---\n", "corrompido"),
        ("---\n- lista\n---\n", "não é um mapa"),
    ],
)
def test_load_frontmatter_invalido(root: Path, conteudo: str, motivo: str) -> None:
    """Frontmatter ausente, não fechado, YAML inválido ou não mapa → InvalidSkillError."""
    pasta = root / "skills" / "alfa"
    pasta.mkdir()
    (pasta / "SKILL.md").write_text(conteudo, encoding="utf-8")
    with pytest.raises(InvalidSkillError) as info:
        FilesystemSkillRepository(root / "skills").load("alfa")
    assert motivo in str(info.value)


def test_load_skill_md_ilegivel(root: Path) -> None:
    """SKILL.md que não é arquivo legível → InvalidSkillError (sem traceback)."""
    (root / "skills" / "alfa" / "SKILL.md").mkdir(parents=True)
    with pytest.raises(InvalidSkillError):
        FilesystemSkillRepository(root / "skills").load("alfa")


def test_content_hash_estavel_e_sensivel(root: Path) -> None:
    """Hash estável; muda ao alterar arquivo; ignora marcador e __pycache__."""
    pasta = escrever_skill(root, "alfa", authored=True, arquivos={"ref/a.md": "a"})
    repo = FilesystemSkillRepository(root / "skills")
    original = repo.content_hash("alfa")
    assert len(original) == 64
    assert repo.content_hash("alfa") == original

    (pasta / ".praxisforge-skill.json").write_text("{}", encoding="utf-8")
    (pasta / "__pycache__").mkdir()
    (pasta / "__pycache__" / "x.pyc").write_bytes(b"x")
    assert repo.content_hash("alfa") == original

    (pasta / "ref" / "a.md").write_text("b", encoding="utf-8")
    assert repo.content_hash("alfa") != original


def test_content_hash_considera_nome_do_arquivo(root: Path) -> None:
    """Renomear um arquivo muda o hash mesmo com os mesmos bytes."""
    pasta = escrever_skill(root, "alfa", authored=True, arquivos={"a.md": "x"})
    repo = FilesystemSkillRepository(root / "skills")
    antes = repo.content_hash("alfa")
    (pasta / "a.md").rename(pasta / "b.md")
    assert repo.content_hash("alfa") != antes


def test_skill_dir(root: Path) -> None:
    """skill_dir aponta para skills/<nome>."""
    assert FilesystemSkillRepository(root / "skills").skill_dir("alfa") == root / "skills" / "alfa"
