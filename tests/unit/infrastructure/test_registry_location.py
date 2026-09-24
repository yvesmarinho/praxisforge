# -*- coding: utf-8 -*-
"""
NOME: test_registry_location.py
TITULO: Testes de falha — resolução do local do registro e detecção do registro antigo
DATA: 24/09/2026 14:30
MODIFICADO: 24/09/2026 14:30
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.registry_location
HISTÓRICO:
    - 24/09/2026 14:30: criação (T003/T004, feature 007)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.infrastructure.registry_location import (
    find_legacy_registry,
    resolve_registry_path,
)

HOME = Path("/casa/curador")
CWD = Path("/trabalho/projeto")


def _resolver(cli: Path | None = None, **env: str) -> Path:
    return resolve_registry_path(cli, env, HOME, CWD)


# --- resolve_registry_path (FR-001, FR-002, FR-012) -------------------------------------


def test_fallback_em_home_config() -> None:
    """Sem variáveis nem opção: ~/.config/praxisforge/folders.yaml."""
    assert _resolver() == HOME / ".config" / "praxisforge" / "folders.yaml"


def test_xdg_absoluta() -> None:
    """XDG_CONFIG_HOME absoluta define a base."""
    assert _resolver(XDG_CONFIG_HOME="/xdg") == Path("/xdg/praxisforge/folders.yaml")


@pytest.mark.parametrize("valor", ["", "relativo/cfg", "./cfg"])
def test_xdg_vazia_ou_relativa_cai_no_fallback(valor: str) -> None:
    """Valor vazio ou relativo é ignorado (especificação XDG)."""
    assert _resolver(XDG_CONFIG_HOME=valor) == HOME / ".config" / "praxisforge" / "folders.yaml"


def test_variavel_do_projeto_vence_xdg() -> None:
    """PRAXISFORGE_REGISTRY tem precedência sobre XDG."""
    resultado = _resolver(PRAXISFORGE_REGISTRY="/dados/reg.yaml", XDG_CONFIG_HOME="/xdg")
    assert resultado == Path("/dados/reg.yaml")


def test_variavel_do_projeto_vazia_eh_ignorada() -> None:
    """PRAXISFORGE_REGISTRY vazia não conta."""
    assert _resolver(PRAXISFORGE_REGISTRY="", XDG_CONFIG_HOME="/xdg") == Path(
        "/xdg/praxisforge/folders.yaml"
    )


def test_opcao_vence_tudo() -> None:
    """--registry tem a maior precedência."""
    resultado = _resolver(
        Path("/opcao/reg.yaml"), PRAXISFORGE_REGISTRY="/dados/reg.yaml", XDG_CONFIG_HOME="/xdg"
    )
    assert resultado == Path("/opcao/reg.yaml")


@pytest.mark.parametrize(
    ("cli", "env", "esperado"),
    [
        (Path("~/reg.yaml"), {}, HOME / "reg.yaml"),
        (None, {"PRAXISFORGE_REGISTRY": "~/outro.yaml"}, HOME / "outro.yaml"),
        (Path("dados/reg.yaml"), {}, CWD / "dados" / "reg.yaml"),
        (None, {"PRAXISFORGE_REGISTRY": "rel.yaml"}, CWD / "rel.yaml"),
    ],
)
def test_til_e_relativo_sao_resolvidos(
    cli: Path | None, env: dict[str, str], esperado: Path
) -> None:
    """~ expandido com o home recebido; relativo resolvido contra o cwd (FR-002)."""
    assert resolve_registry_path(cli, env, HOME, CWD) == esperado


# --- find_legacy_registry (FR-008) ------------------------------------------------------


def _legado(raiz: Path, conteudo: str | None) -> Path:
    arquivo = raiz / "src" / "data" / "folders.yaml"
    if conteudo is not None:
        arquivo.parent.mkdir(parents=True)
        arquivo.write_text(conteudo, encoding="utf-8")
    return arquivo


def test_legado_com_pastas_eh_encontrado(tmp_path: Path) -> None:
    """Registro antigo com ao menos uma pasta é devolvido."""
    arquivo = _legado(tmp_path, "schema_version: '2'\nfolders:\n  a:\n    path: /x\n")
    assert find_legacy_registry(tmp_path) == arquivo


@pytest.mark.parametrize(
    "conteudo",
    [None, "schema_version: '2'\nfolders: {}\n", "folders: [x\n", "- lista\n", "folders: 3\n"],
)
def test_legado_ausente_vazio_ou_invalido_eh_none(tmp_path: Path, conteudo: str | None) -> None:
    """Ausente, sem pastas ou YAML inválido/inesperado → None."""
    _legado(tmp_path, conteudo)
    assert find_legacy_registry(tmp_path) is None
