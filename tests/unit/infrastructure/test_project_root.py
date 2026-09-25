# -*- coding: utf-8 -*-
"""
NOME: test_project_root.py
TITULO: Testes de falha — localização da raiz do projeto praxisforge
DATA: 25/09/2026 09:55
MODIFICADO: 25/09/2026 09:55
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.project_root
HISTÓRICO:
    - 25/09/2026 09:55: criação — CLI deixa de depender do diretório atual
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.domain.errors import ProjectRootNotFoundError
from praxisforge.infrastructure.project_root import find_project_root

_MARCADOR = '[project]\nname = "praxisforge"\n'


def _raiz(base: Path, conteudo: str = _MARCADOR) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    (base / "pyproject.toml").write_text(conteudo, encoding="utf-8")
    return base


def test_cwd_na_raiz(tmp_path: Path) -> None:
    """cwd já é a raiz → devolve o próprio cwd."""
    raiz = _raiz(tmp_path / "repo")
    assert find_project_root(raiz, {}) == raiz


def test_sobe_a_partir_de_subpasta(tmp_path: Path) -> None:
    """cwd em subpasta profunda → sobe até a raiz."""
    raiz = _raiz(tmp_path / "repo")
    sub = raiz / "skills" / "x" / "y"
    sub.mkdir(parents=True)
    assert find_project_root(sub, {}) == raiz


def test_pyproject_de_outro_projeto_e_ignorado(tmp_path: Path) -> None:
    """pyproject.toml de outro projeto no caminho não é a raiz; continua subindo."""
    raiz = _raiz(tmp_path / "repo")
    outro = _raiz(raiz / "vendor" / "lib", '[project]\nname = "outro"\n')
    assert find_project_root(outro, {}) == raiz


@pytest.mark.parametrize("conteudo", ["isto não é toml [[[", "[tool.ruff]\nline-length = 1\n", ""])
def test_pyproject_invalido_ou_sem_project_nao_e_raiz(tmp_path: Path, conteudo: str) -> None:
    """TOML inválido, sem [project] ou vazio não derruba a busca nem vira raiz."""
    raiz = _raiz(tmp_path / "repo")
    sub = _raiz(raiz / "sub", conteudo)
    assert find_project_root(sub, {}) == raiz


def test_fora_de_qualquer_projeto_levanta_erro(tmp_path: Path) -> None:
    """Nenhum ancestral é a raiz → ProjectRootNotFoundError."""
    pasta = tmp_path / "solta"
    pasta.mkdir()
    with pytest.raises(ProjectRootNotFoundError):
        find_project_root(pasta, {})


def test_env_sobrepoe_a_busca(tmp_path: Path) -> None:
    """PRAXISFORGE_ROOT válido vence a busca pelo cwd."""
    raiz = _raiz(tmp_path / "repo")
    fora = tmp_path / "fora"
    fora.mkdir()
    assert find_project_root(fora, {"PRAXISFORGE_ROOT": str(raiz)}) == raiz


def test_env_vazio_e_ignorado(tmp_path: Path) -> None:
    """PRAXISFORGE_ROOT vazio equivale a não definido."""
    raiz = _raiz(tmp_path / "repo")
    assert find_project_root(raiz, {"PRAXISFORGE_ROOT": ""}) == raiz


def test_env_relativo_levanta_erro(tmp_path: Path) -> None:
    """PRAXISFORGE_ROOT relativo é recusado (fail fast), mesmo com cwd válido."""
    raiz = _raiz(tmp_path / "repo")
    with pytest.raises(ProjectRootNotFoundError, match="absoluto"):
        find_project_root(raiz, {"PRAXISFORGE_ROOT": "repo"})


@pytest.mark.parametrize("caso", ["inexistente", "sem_marcador", "arquivo"])
def test_env_que_nao_e_raiz_levanta_erro(tmp_path: Path, caso: str) -> None:
    """PRAXISFORGE_ROOT inexistente, sem marcador ou arquivo → erro, sem cair na busca."""
    raiz = _raiz(tmp_path / "repo")
    alvo = tmp_path / caso
    if caso == "sem_marcador":
        alvo.mkdir()
    elif caso == "arquivo":
        alvo.write_text("x", encoding="utf-8")
    with pytest.raises(ProjectRootNotFoundError, match="PRAXISFORGE_ROOT"):
        find_project_root(raiz, {"PRAXISFORGE_ROOT": str(alvo)})


def test_pyproject_ilegivel_nao_e_raiz(tmp_path: Path) -> None:
    """pyproject.toml que é diretório (ilegível como arquivo) não derruba a busca."""
    raiz = _raiz(tmp_path / "repo")
    sub = raiz / "sub"
    (sub / "pyproject.toml").mkdir(parents=True)
    assert find_project_root(sub, {}) == raiz
