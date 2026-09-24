# -*- coding: utf-8 -*-
"""
NOME: test_cli_skills_publish.py
TITULO: Testes de integração — CLI praxisforge skills publish (feature 008)
DATA: 24/09/2026 16:48
MODIFICADO: 24/09/2026 16:49
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 24/09/2026 16:48: criação (T030, feature 008)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main
from tests.skills_helpers import criar_projeto, escrever_skill


@pytest.fixture
def projeto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = criar_projeto(tmp_path / "projeto")
    monkeypatch.chdir(root)
    return root


def _global() -> Path:
    return Path.home() / ".claude" / "skills"


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _mtimes(pasta: Path) -> dict[str, int]:
    return {str(p): p.stat().st_mtime_ns for p in sorted(pasta.rglob("*"))}


def test_publica_global_e_repete_sem_mudanca(
    projeto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--target global → ~/.claude/skills/<nome>/; 2ª execução não altera nada (SC-003)."""
    escrever_skill(projeto, "alfa", authored=True)
    code, out, _ = _run(["skills", "publish", "alfa", "--target", "global"], capsys)
    assert code == 0 and "alfa → publicada" in out
    assert (_global() / "alfa" / "SKILL.md").is_file()
    antes = _mtimes(_global())
    code, out, _ = _run(["skills", "publish", "alfa", "--target", "global"], capsys)
    assert code == 0 and "alfa → inalterada" in out
    assert _mtimes(_global()) == antes


def test_publica_em_pasta_de_projeto(
    projeto: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--target <pasta> → <pasta>/.claude/skills/<nome>/ (symlink)."""
    escrever_skill(projeto, "alfa", authored=True)
    outro = tmp_path / "outro-projeto"
    outro.mkdir()
    code, out, _ = _run(
        ["skills", "publish", "--all", "--target", str(outro), "--mode", "symlink"], capsys
    )
    assert code == 0 and "alfa → publicada" in out
    assert (outro / ".claude" / "skills" / "alfa").is_symlink()


def test_mudanca_sem_versao_recusada(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Conteúdo alterado com a mesma versão → recusada, exit 1; com nova versão → atualizada."""
    pasta = escrever_skill(projeto, "alfa", authored=True)
    _run(["skills", "publish", "alfa", "--target", "global"], capsys)
    (pasta / "extra.md").write_text("novo", encoding="utf-8")
    code, out, _ = _run(["skills", "publish", "alfa", "--target", "global"], capsys)
    assert code == 1 and "alfa → recusada (" in out and "versão" in out
    assert not (_global() / "alfa" / "extra.md").exists()
    escrever_skill(projeto, "alfa", authored=True, version="1.0.1")
    code, out, _ = _run(["skills", "publish", "alfa", "--target", "global"], capsys)
    assert code == 0 and "alfa → atualizada" in out


def test_terceiro_intacto(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Skill de mesmo nome não publicada pelo praxisforge fica intacta (SC-004)."""
    escrever_skill(projeto, "alfa", authored=True)
    alheia = _global() / "alfa"
    alheia.mkdir(parents=True)
    (alheia / "SKILL.md").write_text("minha", encoding="utf-8")
    code, out, _ = _run(["skills", "publish", "--all", "--target", "global"], capsys)
    assert code == 1 and "alfa → recusada (" in out
    assert (alheia / "SKILL.md").read_text(encoding="utf-8") == "minha"


def test_orfa_listada_e_removida_com_prune(
    projeto: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Órfã nossa é listada com --all e removida só com --prune."""
    pasta = escrever_skill(projeto, "velha", authored=True)
    _run(["skills", "publish", "velha", "--target", "global"], capsys)
    for item in sorted(pasta.rglob("*"), reverse=True):
        item.unlink()
    pasta.rmdir()
    code, out, _ = _run(["skills", "publish", "--all", "--target", "global"], capsys)
    assert code == 0 and "órfã: velha" in out
    assert (_global() / "velha").exists()
    code, out, _ = _run(["skills", "publish", "--all", "--target", "global", "--prune"], capsys)
    assert code == 0 and "órfã: velha (removida)" in out
    assert not (_global() / "velha").exists()


def test_invalida_recusada(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Skill inválida não é publicada."""
    escrever_skill(projeto, "alfa", version="1")
    code, out, _ = _run(["skills", "publish", "alfa", "--target", "global"], capsys)
    assert code == 1 and "alfa → recusada (" in out
    assert not (_global() / "alfa").exists()


def test_sem_permissao_exit_3(projeto: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Destino sem permissão de escrita → exit 3."""
    escrever_skill(projeto, "alfa", authored=True)
    _global().mkdir(parents=True)
    _global().chmod(0o500)
    try:
        code, out, _ = _run(["skills", "publish", "alfa", "--target", "global"], capsys)
    finally:
        _global().chmod(0o700)
    assert code == 3 and "alfa → recusada (" in out


@pytest.mark.parametrize(
    "argv",
    [
        ["skills", "publish", "--target", "global"],
        ["skills", "publish", "alfa", "--all", "--target", "global"],
        ["skills", "publish", "alfa", "--target", "global", "--prune"],
        ["skills", "publish", "alfa", "--target", "/nao/existe/mesmo"],
    ],
)
def test_uso_incorreto_exit_2(
    projeto: Path, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """Sem nome/--all, ambos, --prune sem --all, ou pasta de projeto inexistente → exit 2."""
    escrever_skill(projeto, "alfa", authored=True)
    code, _, err = _run(argv, capsys)
    assert code == 2 and err


def test_target_obrigatorio(projeto: Path) -> None:
    """--target é obrigatório (argparse → exit 2)."""
    with pytest.raises(SystemExit) as info:
        main(["skills", "publish", "alfa"])
    assert info.value.code == 2
