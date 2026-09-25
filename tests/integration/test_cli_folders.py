# -*- coding: utf-8 -*-
"""
NOME: test_cli_folders.py
TITULO: Testes de falha — CLI praxisforge folders add|list|show|update
DATA: 22/09/2026 09:45
MODIFICADO: 25/09/2026 09:52
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 09:45: criação (T032)
    - 22/09/2026 19:08: +caso update --status ignore (T029, feature 003-bootstrap-registro-pastas)
    - 23/09/2026 12:08: versão curada em update/show (T019, feature 004)
    - 23/09/2026 16:53: --path obrigatório, caminho em list/show (T022, feature 005)
    - 24/09/2026 10:56: política máxima em show/list (T023, feature 006)
    - 25/09/2026 09:52: folders update --description
STATUS: DEV
"""

import os
import subprocess
from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _pasta(registry_path: Path, nome: str = "exemplo") -> Path:
    """Cria (se preciso) uma pasta real ao lado do registro para os testes de add."""
    pasta = registry_path.parent / "pastas" / nome
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_add_list_show_update_fluxo_completo(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fluxo completo add → list → show → update com código 0 em cada passo."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    code, out, _ = _run(
        [
            *registry_arg,
            "folders",
            "add",
            "--alias",
            "exemplo",
            "--description",
            "Pasta de teste",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--path",
            str(_pasta(tmp_registry_path)),
            "--status",
            "not_scanned",
        ],
        capsys,
    )
    assert code == 0

    code, out, _ = _run([*registry_arg, "folders", "list"], capsys)
    assert code == 0
    assert "exemplo" in out
    assert out.rstrip().endswith(str(_pasta(tmp_registry_path)))  # caminho na última coluna

    code, out, _ = _run([*registry_arg, "folders", "show", "exemplo"], capsys)
    assert code == 0
    assert "exemplo" in out
    assert f"caminho: {_pasta(tmp_registry_path)}" in out

    code, out, _ = _run(
        [*registry_arg, "folders", "update", "exemplo", "--status", "scanned"], capsys
    )
    assert code == 0


def test_add_duas_vezes_identico_imprime_inalterado_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Segundo add idêntico imprime 'inalterado' e retorna código 0."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    args = [
        *registry_arg,
        "folders",
        "add",
        "--alias",
        "exemplo",
        "--description",
        "Pasta de teste",
        "--content-type",
        "documents",
        "--license",
        "MIT",
        "--path",
        str(_pasta(tmp_registry_path)),
        "--status",
        "not_scanned",
    ]
    _run(args, capsys)
    code, out, _ = _run(args, capsys)
    assert code == 0
    assert "inalterado" in out


def test_add_duplicado_com_dados_diferentes_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """add de alias já registrado com dados diferentes retorna código 1."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    base = [
        *registry_arg,
        "folders",
        "add",
        "--alias",
        "exemplo",
        "--description",
        "Pasta de teste",
        "--content-type",
        "documents",
        "--license",
        "MIT",
        "--path",
        str(_pasta(tmp_registry_path)),
        "--status",
        "not_scanned",
    ]
    _run(base, capsys)
    outro = [*base[:-1], "not_scanned"]
    outro[base.index("--description") + 1] = "Outra descrição"
    code, _, err = _run(outro, capsys)
    assert code == 1
    assert err


def test_show_alias_inexistente_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """show de alias inexistente retorna código 1."""
    tmp_registry_path.write_text("schema_version: '2'\nfolders: {}\n", encoding="utf-8")
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "show", "inexistente"], capsys
    )
    assert code == 1
    assert err


def test_mensagens_pt_br_no_stderr(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mensagens de erro estão em pt-BR e vão para stderr."""
    tmp_registry_path.write_text("schema_version: '2'\nfolders: {}\n", encoding="utf-8")
    _, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "show", "inexistente"], capsys
    )
    assert "não encontrada" in err


def test_list_so_expoe_o_caminho_da_propria_pasta(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """list mostra o caminho de cada pasta (FR-013) e nenhum outro caminho (ex.: do registro)."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    _run(
        [
            *registry_arg,
            "folders",
            "add",
            "--alias",
            "exemplo",
            "--description",
            "Pasta de teste",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--path",
            str(_pasta(tmp_registry_path)),
            "--status",
            "not_scanned",
        ],
        capsys,
    )
    code, out, _ = _run([*registry_arg, "folders", "list"], capsys)
    assert str(tmp_registry_path) not in out
    assert str(_pasta(tmp_registry_path)) in out


def test_update_status_ignore_aceito_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders update --status ignore é aceito mesmo com licença unknown (FR-011)."""
    registry_arg = ["--registry", str(tmp_registry_path)]
    _run(
        [
            *registry_arg,
            "folders",
            "add",
            "--alias",
            "pasta_tecnica",
            "--description",
            "Pasta técnica",
            "--content-type",
            "unclassified",
            "--license",
            "unknown",
            "--path",
            str(_pasta(tmp_registry_path)),
            "--status",
            "pending",
        ],
        capsys,
    )
    code, out, _ = _run(
        [*registry_arg, "folders", "update", "pasta_tecnica", "--status", "ignore"], capsys
    )
    assert code == 0


# --- feature 004: versão curada (US1) --------------------------------------------------

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Teste",
    "GIT_AUTHOR_EMAIL": "teste@example.invalid",
    "GIT_COMMITTER_NAME": "Teste",
    "GIT_COMMITTER_EMAIL": "teste@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **_GIT_ENV},
    )
    return result.stdout.strip()


def _repo_git(base: Path) -> tuple[Path, str]:
    repo = base / "fonte"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("fonte\n", encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-q", "-m", "inicial")
    return repo, _git(repo, "rev-parse", "HEAD")


def _registrar(registry: Path, capsys: pytest.CaptureFixture[str], caminho: Path) -> None:
    code, _, _ = _run(
        [
            "--registry",
            str(registry),
            "folders",
            "add",
            "--alias",
            "fonte",
            "--description",
            "Fonte curada",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--path",
            str(caminho),
            "--status",
            "in_curation",
        ],
        capsys,
    )
    assert code == 0


def test_update_curated_em_pasta_git_grava_e_exibe_versao(
    tmp_path: Path, tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders update --status curated grava o HEAD e show exibe 12 caracteres (FR-001, FR-011)."""
    repo, head = _repo_git(tmp_path)
    _registrar(tmp_registry_path, capsys, repo)
    registry_arg = ["--registry", str(tmp_registry_path)]

    code, out, _ = _run(
        [*registry_arg, "folders", "update", "fonte", "--status", "curated"], capsys
    )
    assert code == 0
    assert f"versão curada: {head[:12]}" in out
    assert str(tmp_path) not in out
    assert f"last_curated_commit: {head}" in tmp_registry_path.read_text(encoding="utf-8")

    code, out, _ = _run([*registry_arg, "folders", "show", "fonte"], capsys)
    assert code == 0
    assert f"versão curada: {head[:12]}" in out


def test_update_curated_em_pasta_nao_git_informa(
    tmp_path: Path, tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pasta não-git: status muda e a saída explica que não há versão (FR-002)."""
    pasta = tmp_path / "solta"
    pasta.mkdir()
    _registrar(tmp_registry_path, capsys, pasta)
    registry_arg = ["--registry", str(tmp_registry_path)]

    code, out, _ = _run(
        [*registry_arg, "folders", "update", "fonte", "--status", "curated"], capsys
    )
    assert code == 0
    assert "versão curada: (pasta não é repositório git)" in out

    code, out, _ = _run([*registry_arg, "folders", "show", "fonte"], capsys)
    assert "versão curada: -" in out


def test_update_curated_com_pasta_movida_sai_com_3_sem_alterar(
    tmp_path: Path, tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pasta que sumiu do caminho registrado → exit 3 e YAML inalterado (FR-003 da 004)."""
    pasta = tmp_path / "fonte"
    pasta.mkdir()
    _registrar(tmp_registry_path, capsys, pasta)
    pasta.rmdir()
    antes = tmp_registry_path.read_bytes()
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "update", "fonte", "--status", "curated"],
        capsys,
    )
    assert code == 3
    assert "fonte" in err
    assert tmp_registry_path.read_bytes() == antes


# --- feature 005: caminho no registro (US1) ---------------------------------------------


def _add(
    registry: Path, alias: str, caminho: str, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    return _run(
        [
            "--registry",
            str(registry),
            "folders",
            "add",
            "--alias",
            alias,
            "--description",
            "d",
            "--content-type",
            "documents",
            "--license",
            "MIT",
            "--path",
            caminho,
        ],
        capsys,
    )


def test_add_sem_path_eh_uso_incorreto(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--path é obrigatório em add (FR-004)."""
    with pytest.raises(SystemExit) as info:
        _run(
            [
                "--registry",
                str(tmp_registry_path),
                "folders",
                "add",
                "--alias",
                "exemplo",
                "--description",
                "d",
                "--content-type",
                "documents",
                "--license",
                "MIT",
            ],
            capsys,
        )
    assert info.value.code == 2


def test_add_caminho_inexistente_sai_com_3(
    tmp_path: Path, tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Caminho inexistente → exit 3, nada gravado."""
    code, _, err = _add(tmp_registry_path, "exemplo", str(tmp_path / "nao_existe"), capsys)
    assert code == 3
    assert "exemplo" in err
    assert not tmp_registry_path.exists()


def test_add_caminho_duplicado_sai_com_1_citando_dono(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Mesmo caminho sob outro alias → exit 1 citando o alias existente (FR-003)."""
    pasta = _pasta(tmp_registry_path)
    assert _add(tmp_registry_path, "exemplo", str(pasta), capsys)[0] == 0
    code, _, err = _add(tmp_registry_path, "outro", str(pasta).upper(), capsys)
    assert code in (1, 3)  # maiúsculas podem não existir no disco: nunca grava
    code, _, err = _add(tmp_registry_path, "outro", f"{pasta}/", capsys)
    assert code == 1
    assert "exemplo" in err


def test_update_path_move_a_pasta_preservando_dados(
    tmp_path: Path, tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """update --path corrige pasta movida mantendo status (FR-016)."""
    pasta = _pasta(tmp_registry_path)
    _add(tmp_registry_path, "exemplo", str(pasta), capsys)
    nova = tmp_path / "movida"
    pasta.rename(nova)
    registry_arg = ["--registry", str(tmp_registry_path)]
    code, _, err = _run(
        [*registry_arg, "folders", "update", "exemplo", "--path", str(nova)], capsys
    )
    assert code == 0, err
    _, out, _ = _run([*registry_arg, "folders", "show", "exemplo"], capsys)
    assert f"caminho: {nova}" in out
    assert "status: não varrida" in out


def _add_com_licenca(
    registry: Path, alias: str, licenca: str, capsys: pytest.CaptureFixture[str]
) -> Path:
    pasta = _pasta(registry, alias)
    code, _, err = _run(
        [
            "--registry",
            str(registry),
            "folders",
            "add",
            "--alias",
            alias,
            "--description",
            "d",
            "--content-type",
            "documents",
            "--license",
            licenca,
            "--path",
            str(pasta),
            "--status",
            "not_scanned",
        ],
        capsys,
    )
    assert code == 0, err
    return pasta


def test_show_exibe_politica_maxima(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """show: linha 'política máxima' derivada da licença (FR-013, SC-004)."""
    _add_com_licenca(tmp_registry_path, "fonte_mit", "MIT", capsys)
    _add_com_licenca(tmp_registry_path, "fonte_mpl", "MPL-2.0", capsys)
    registry_arg = ["--registry", str(tmp_registry_path)]

    code, out, _ = _run([*registry_arg, "folders", "show", "fonte_mit"], capsys)
    assert code == 0
    assert "política máxima: verbatim\n" in out

    code, out, _ = _run([*registry_arg, "folders", "show", "fonte_mpl"], capsys)
    assert "política máxima: link (licença não classificada)" in out


def test_list_exibe_politica_apos_status_e_caminho_por_ultimo(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """list: política logo após o status; caminho continua a última coluna."""
    pasta = _add_com_licenca(tmp_registry_path, "fonte_mit", "MIT", capsys)
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "list"], capsys)
    assert code == 0
    colunas = out.strip().split("\t")
    assert colunas[0] == "fonte_mit"
    assert colunas[3] == "não varrida"
    assert colunas[4] == "verbatim"
    assert colunas[-1] == str(pasta)


# --- folders update --description -------------------------------------------------------


def test_update_description_codigo_0_e_show_exibe(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders update --description troca a descrição exibida por show."""
    _registrar(tmp_registry_path, capsys, _pasta(tmp_registry_path))
    registry_arg = ["--registry", str(tmp_registry_path)]
    code, _, _ = _run(
        [*registry_arg, "folders", "update", "fonte", "--description", "Descrição corrigida"],
        capsys,
    )
    assert code == 0
    _, out, _ = _run([*registry_arg, "folders", "show", "fonte"], capsys)
    assert "descrição: Descrição corrigida" in out


def test_update_description_vazia_codigo_2_sem_alterar(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--description vazia é erro de uso (código 2) e não altera o registro."""
    _registrar(tmp_registry_path, capsys, _pasta(tmp_registry_path))
    antes = tmp_registry_path.read_bytes()
    code, _, err = _run(
        ["--registry", str(tmp_registry_path), "folders", "update", "fonte", "--description", ""],
        capsys,
    )
    assert code == 2
    assert "argumentos inválidos" in err
    assert tmp_registry_path.read_bytes() == antes
