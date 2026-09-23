# -*- coding: utf-8 -*-
"""
NOME: test_git_cli_inspector.py
TITULO: Testes de integração — GitCliInspector com repositórios git reais
DATA: 23/09/2026 12:05
MODIFICADO: 23/09/2026 12:05
VERSÃO: 0.1.0
DEPEND: pytest, git (executável), praxisforge.infrastructure.git_cli_inspector
HISTÓRICO:
    - 23/09/2026 12:05: criação (T007, T008 — feature 004-deteccao-mudanca-conteudo)
STATUS: DEV
"""

import os
import subprocess
from pathlib import Path

import pytest

from praxisforge.domain.errors import ContentInspectionError
from praxisforge.infrastructure.git_cli_inspector import GitCliInspector

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Teste",
    "GIT_AUTHOR_EMAIL": "teste@example.invalid",
    "GIT_COMMITTER_NAME": "Teste",
    "GIT_COMMITTER_EMAIL": "teste@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(repo: Path, *args: str) -> str:
    env = {**os.environ, **_GIT_ENV}
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _commit(repo: Path, relpath: str, content: str) -> str:
    arquivo = repo / relpath
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(content, encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-q", "-m", f"altera {relpath}")
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    raiz = tmp_path / "repo"
    raiz.mkdir()
    _git(raiz, "init", "-q", "-b", "main")
    _commit(raiz, "sub/a.txt", "a1")
    _commit(raiz, "fora/b.txt", "b1")
    return raiz


# --- head_commit -----------------------------------------------------------------------


def test_head_commit_na_raiz_retorna_hash(repo: Path) -> None:
    """Pasta raiz de repositório → hash do HEAD (40 hex)."""
    head = GitCliInspector().head_commit(repo)
    assert head == _git(repo, "rev-parse", "HEAD")
    assert len(head or "") == 40


def test_head_commit_em_subpasta_retorna_hash_do_repositorio(repo: Path) -> None:
    """Subpasta de repositório → mesmo HEAD do repositório."""
    assert GitCliInspector().head_commit(repo / "sub") == _git(repo, "rev-parse", "HEAD")


def test_head_commit_pasta_nao_git_retorna_none(tmp_path: Path) -> None:
    """Pasta fora de repositório → None (FR-002)."""
    pasta = tmp_path / "solta"
    pasta.mkdir()
    assert GitCliInspector().head_commit(pasta) is None


def test_head_commit_repositorio_sem_commits_retorna_none(tmp_path: Path) -> None:
    """Repositório sem commits → None (mesmo tratamento de não-git)."""
    vazio = tmp_path / "vazio"
    vazio.mkdir()
    _git(vazio, "init", "-q")
    assert GitCliInspector().head_commit(vazio) is None


# --- changed_since ---------------------------------------------------------------------


def test_sem_commits_novos_nao_mudou(repo: Path) -> None:
    """HEAD igual ao gravado → False."""
    head = _git(repo, "rev-parse", "HEAD")
    assert GitCliInspector().changed_since(repo, head) is False


def test_commit_fora_da_subpasta_nao_conta(repo: Path) -> None:
    """Commit só fora da subpasta → False (Clarificação Q3)."""
    gravado = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "fora/b.txt", "b2")
    assert GitCliInspector().changed_since(repo / "sub", gravado) is False


def test_commit_dentro_da_subpasta_conta(repo: Path) -> None:
    """Commit alterando arquivo da subpasta → True (FR-005)."""
    gravado = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "sub/a.txt", "a2")
    assert GitCliInspector().changed_since(repo / "sub", gravado) is True


def test_commit_na_raiz_conta_para_a_raiz(repo: Path) -> None:
    """Qualquer arquivo alterado conta quando a pasta é a raiz."""
    gravado = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "fora/b.txt", "b2")
    assert GitCliInspector().changed_since(repo, gravado) is True


def test_commit_gravado_inexistente_conta_como_mudanca(repo: Path) -> None:
    """Hash válido mas ausente do histórico (reescrita) → True."""
    assert GitCliInspector().changed_since(repo, "f" * 40) is True


def test_head_retrocedido_com_conteudo_diferente_conta(repo: Path) -> None:
    """Checkout de versão antiga com conteúdo diferente na pasta → True."""
    antigo = _git(repo, "rev-parse", "HEAD")
    novo = _commit(repo, "sub/a.txt", "a2")
    _git(repo, "checkout", "-q", antigo)
    assert GitCliInspector().changed_since(repo / "sub", novo) is True


def test_alteracao_nao_commitada_e_ignorada_nao_contam(repo: Path) -> None:
    """Working tree sujo e arquivos ignorados não contam como mudança."""
    gravado = _git(repo, "rev-parse", "HEAD")
    (repo / "sub" / "a.txt").write_text("sujo", encoding="utf-8")
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (repo / "sub" / "x.log").write_text("log", encoding="utf-8")
    assert GitCliInspector().changed_since(repo / "sub", gravado) is False


def test_mudanca_do_ponteiro_de_submodulo_conta(repo: Path, tmp_path: Path) -> None:
    """Troca do commit apontado por um submódulo dentro da pasta → True (FR-017)."""
    externo = tmp_path / "externo"
    externo.mkdir()
    _git(externo, "init", "-q", "-b", "main")
    _commit(externo, "x.txt", "x1")
    _git(
        repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(externo), "sub/mod"
    )
    _git(repo, "commit", "-q", "-m", "adiciona submódulo")
    gravado = _git(repo, "rev-parse", "HEAD")
    _commit(externo, "x.txt", "x2")
    _git(repo / "sub" / "mod", "pull", "-q", "origin", "main")
    _git(repo, "add", "sub/mod")
    _git(repo, "commit", "-q", "-m", "avança submódulo")
    assert GitCliInspector().changed_since(repo / "sub", gravado) is True


# --- falhas (FR-009) -------------------------------------------------------------------


def test_git_ausente_levanta_content_inspection_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Executável git indisponível → ContentInspectionError, sem caminho na mensagem."""
    monkeypatch.setenv("PATH", "")
    with pytest.raises(ContentInspectionError) as info:
        GitCliInspector().head_commit(repo)
    assert str(repo) not in str(info.value)


def test_timeout_levanta_content_inspection_error(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Chamada git que excede o limite → ContentInspectionError."""

    def _estoura(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="git", timeout=10)

    monkeypatch.setattr(subprocess, "run", _estoura)
    with pytest.raises(ContentInspectionError) as info:
        GitCliInspector().changed_since(repo, "a" * 40)
    assert str(repo) not in str(info.value)


def test_repositorio_corrompido_levanta_content_inspection_error(repo: Path) -> None:
    """HEAD corrompido → código de saída inesperado → ContentInspectionError."""
    (repo / ".git" / "HEAD").write_text("lixo\n", encoding="utf-8")
    (repo / ".git" / "refs").rename(repo / ".git" / "refs_quebrado")
    with pytest.raises(ContentInspectionError) as info:
        GitCliInspector().changed_since(repo, "a" * 40)
    assert str(repo) not in str(info.value)


@pytest.mark.parametrize("valor", ["HEAD", "--output=/tmp/x", "a" * 39, "A" * 40, ""])
def test_hash_malformado_nunca_chega_ao_git(
    repo: Path, monkeypatch: pytest.MonkeyPatch, valor: str
) -> None:
    """Hash fora do formato é recusado antes de montar a linha de comando."""
    chamadas: list[object] = []
    original = subprocess.run

    def _espiao(*args: object, **kwargs: object) -> object:
        chamadas.append(args)
        return original(*args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(subprocess, "run", _espiao)
    with pytest.raises(ContentInspectionError):
        GitCliInspector().changed_since(repo, valor)
    assert all(valor not in str(chamada) for chamada in chamadas if valor)
