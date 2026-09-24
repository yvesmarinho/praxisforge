# -*- coding: utf-8 -*-
"""
NOME: test_cli_registry_location.py
TITULO: Testes de falha — CLI com o registro no local padrão fora do repositório (feature 007)
DATA: 24/09/2026 14:32
MODIFICADO: 24/09/2026 14:32
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 24/09/2026 14:32: criação (T010/T011, US1; T019/T020, US2, feature 007)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _add(pasta: Path, capsys: pytest.CaptureFixture[str], *extra: str) -> tuple[int, str, str]:
    pasta.mkdir(parents=True, exist_ok=True)
    return _run(
        [
            *extra,
            "folders",
            "add",
            "--alias",
            "fonte",
            "--description",
            "d",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--path",
            str(pasta),
        ],
        capsys,
    )


def _padrao(tmp_path: Path) -> Path:
    return tmp_path / "xdg" / "praxisforge" / "folders.yaml"


# --- US1: local padrão (FR-001, FR-003) --------------------------------------------------


def test_add_sem_registry_cria_no_local_padrao_xdg(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Sem --registry: registro criado em $XDG_CONFIG_HOME/praxisforge/folders.yaml."""
    code, _, err = _add(tmp_path / "pastas" / "fonte", capsys)
    assert code == 0, err
    assert _padrao(tmp_path).is_file()
    code, out, _ = _run(["folders", "list"], capsys)
    assert code == 0
    assert out.startswith("fonte\t")


def test_bootstrap_sem_registry_cria_no_local_padrao(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """bootstrap também cria o registro (e a pasta) no local padrão."""
    raiz = tmp_path / "raiz"
    (raiz / "repo_a").mkdir(parents=True)
    code, _, err = _run(["folders", "bootstrap", str(raiz)], capsys)
    assert code == 0, err
    assert _padrao(tmp_path).is_file()


def test_sem_xdg_usa_home_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sem XDG_CONFIG_HOME: ~/.config/praxisforge/folders.yaml."""
    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "casa"))
    code, _, err = _add(tmp_path / "pastas" / "fonte", capsys)
    assert code == 0, err
    assert (tmp_path / "casa" / ".config" / "praxisforge" / "folders.yaml").is_file()


# --- US1: registro ausente (FR-004, SC-004) ----------------------------------------------


@pytest.mark.parametrize(
    "comando",
    [
        ["folders", "list"],
        ["folders", "show", "fonte"],
        ["folders", "update", "fonte", "--status", "scanned"],
        ["folders", "resolve", "fonte"],
        ["folders", "resolve", "--all"],
        ["folders", "scan", "fonte"],
        ["folders", "scan", "--all"],
        ["folders", "validate"],
        ["folders", "migrate"],
    ],
)
def test_comandos_de_leitura_com_registro_ausente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], comando: list[str]
) -> None:
    """Exit 1, mensagem com o local resolvido e sugestão de add/bootstrap; nada é criado."""
    code, out, err = _run(comando, capsys)
    assert code == 1
    saida = out + err
    assert str(_padrao(tmp_path)) in saida
    assert "folders add" in saida and "folders bootstrap" in saida
    assert not _padrao(tmp_path).exists()
    assert not _padrao(tmp_path).parent.exists()


# --- US2: precedência e override (FR-001, FR-002, Edge Cases) -----------------------------


def test_variavel_do_projeto_sem_opcao(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """PRAXISFORGE_REGISTRY é usada quando não há --registry."""
    alvo = tmp_path / "var" / "reg.yaml"
    monkeypatch.setenv("PRAXISFORGE_REGISTRY", str(alvo))
    code, _, err = _add(tmp_path / "pastas" / "fonte", capsys)
    assert code == 0, err
    assert alvo.is_file()
    assert not _padrao(tmp_path).exists()


def test_opcao_vence_a_variavel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """--registry tem precedência sobre PRAXISFORGE_REGISTRY."""
    pela_variavel = tmp_path / "var" / "reg.yaml"
    pela_opcao = tmp_path / "opcao" / "reg.yaml"
    monkeypatch.setenv("PRAXISFORGE_REGISTRY", str(pela_variavel))
    code, _, err = _add(tmp_path / "pastas" / "fonte", capsys, "--registry", str(pela_opcao))
    assert code == 0, err
    assert pela_opcao.is_file()
    assert not pela_variavel.exists()


def test_variavel_vazia_eh_ignorada(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """PRAXISFORGE_REGISTRY vazia → local padrão."""
    monkeypatch.setenv("PRAXISFORGE_REGISTRY", "")
    code, _, err = _add(tmp_path / "pastas" / "fonte", capsys)
    assert code == 0, err
    assert _padrao(tmp_path).is_file()


def test_variavel_com_til_eh_expandida(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """~ na variável é expandido para a pasta pessoal."""
    monkeypatch.setenv("HOME", str(tmp_path / "casa"))
    monkeypatch.setenv("PRAXISFORGE_REGISTRY", "~/meu/reg.yaml")
    code, _, err = _add(tmp_path / "pastas" / "fonte", capsys)
    assert code == 0, err
    assert (tmp_path / "casa" / "meu" / "reg.yaml").is_file()


def test_variavel_para_arquivo_inexistente(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Leitura falha como ausente citando o local; add cria nesse local."""
    alvo = tmp_path / "novo" / "reg.yaml"
    monkeypatch.setenv("PRAXISFORGE_REGISTRY", str(alvo))
    code, out, err = _run(["folders", "list"], capsys)
    assert code == 1
    assert str(alvo) in out + err
    code, _, err = _add(tmp_path / "pastas" / "fonte", capsys)
    assert code == 0, err
    assert alvo.is_file()


def test_local_que_eh_diretorio_eh_erro_de_uso(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Local resolvido é diretório → exit 2 citando o local."""
    diretorio = tmp_path / "sou_pasta"
    diretorio.mkdir()
    code, out, err = _run(["--registry", str(diretorio), "folders", "list"], capsys)
    assert code == 2
    assert str(diretorio) in out + err


def test_local_link_simbolico_para_arquivo_eh_seguido(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Link simbólico para o registro é lido normalmente."""
    real = tmp_path / "real" / "reg.yaml"
    _add(tmp_path / "pastas" / "fonte", capsys, "--registry", str(real))
    link = tmp_path / "link.yaml"
    link.symlink_to(real)
    code, out, _ = _run(["--registry", str(link), "folders", "list"], capsys)
    assert code == 0
    assert out.startswith("fonte\t")
