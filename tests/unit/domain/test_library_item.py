# -*- coding: utf-8 -*-
"""
NOME: test_library_item.py
TITULO: Testes de falha — ItemKind, ItemName e LibraryItem do acervo (feature 009)
DATA: 25/09/2026 13:00
MODIFICADO: 25/09/2026 13:00
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.library_item
HISTÓRICO:
    - 25/09/2026 13:00: criação (T010, feature 009) — sucede test_skill.py
STATUS: DEV
"""

from collections.abc import Mapping

import pytest

from praxisforge.domain.errors import InvalidLibraryItemError, UnknownItemKindError
from praxisforge.domain.library_item import ItemKind, ItemName, LibraryItem

META: dict[str, object] = {"version": "1.0.0", "sources": ["guia-a"]}


def _fm(kind: ItemKind, **campos: object) -> dict[str, object]:
    base: dict[str, object] = {"description": "Descrição", "metadata": dict(META)}
    if kind in (ItemKind.SKILL, ItemKind.AGENT, ItemKind.HOOK, ItemKind.REFERENCE):
        base["name"] = "item-a"
    if kind is ItemKind.HOOK:
        base.update(event="SessionStart", run=["run.sh"])
    base.update(campos)
    return base


def _campos(erro: pytest.ExceptionInfo[InvalidLibraryItemError]) -> list[str]:
    return [v.field for v in erro.value.violations]


def _montar(
    kind: ItemKind,
    fm: Mapping[str, object],
    entry: str = "item-a",
    refs: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
) -> LibraryItem:
    return LibraryItem.from_parts(kind, entry, fm, refs, missing)


# --- ItemKind / ItemName ------------------------------------------------------------------


def test_kind_por_texto_e_diretorio() -> None:
    """Cada tipo tem texto e diretório no plural."""
    assert ItemKind.from_str("command") is ItemKind.COMMAND
    assert ItemKind.from_directory("agents") is ItemKind.AGENT
    assert [k.directory for k in ItemKind] == [
        "skills",
        "commands",
        "agents",
        "hooks",
        "rules",
        "references",
    ]


@pytest.mark.parametrize("valor", ["prompt", "", "skills", "Skill"])
def test_kind_desconhecido(valor: str) -> None:
    """Tipo fora dos seis levanta UnknownItemKindError."""
    with pytest.raises(UnknownItemKindError):
        ItemKind.from_str(valor)


def test_diretorio_desconhecido() -> None:
    """Diretório que não é de tipo levanta UnknownItemKindError."""
    with pytest.raises(UnknownItemKindError):
        ItemKind.from_directory("prompts")


def test_publicaveis() -> None:
    """Só skill, command, agent e rule são publicáveis (FR-019)."""
    assert {k for k in ItemKind if k.publishable} == {
        ItemKind.SKILL,
        ItemKind.COMMAND,
        ItemKind.AGENT,
        ItemKind.RULE,
    }


@pytest.mark.parametrize("nome", ["Revisar", "a_b", "-a", "a--b", "x" * 65, ""])
def test_nome_invalido(nome: str) -> None:
    """Nome fora de minúsculas-com-hífen ou > 64 caracteres é recusado."""
    with pytest.raises(InvalidLibraryItemError):
        ItemName(nome)


# --- comuns a todos os tipos ------------------------------------------------------------


@pytest.mark.parametrize("kind", list(ItemKind))
def test_item_valido_de_cada_tipo(kind: ItemKind) -> None:
    """Frontmatter mínimo válido monta o item com o nome da entrada."""
    item = _montar(kind, _fm(kind))
    assert item.kind is kind
    assert item.name == "item-a"
    assert item.version == "1.0.0"
    assert item.sources == ("guia-a",)
    assert item.rewrite_pending is False


@pytest.mark.parametrize("kind", list(ItemKind))
@pytest.mark.parametrize("descricao", [None, "", "   ", "x" * 1025])
def test_descricao_invalida(kind: ItemKind, descricao: object) -> None:
    """Descrição ausente, vazia ou > 1024 caracteres é violação."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(kind, _fm(kind, description=descricao))
    assert "description" in _campos(erro)


@pytest.mark.parametrize("kind", list(ItemKind))
@pytest.mark.parametrize("versao", [None, "1.0", "v1.0.0", 1])
def test_versao_nao_semver(kind: ItemKind, versao: object) -> None:
    """metadata.version ausente ou fora de semver é violação."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(kind, _fm(kind, metadata={"version": versao, "authored": True}))
    assert "metadata.version" in _campos(erro)


def test_metadata_ausente() -> None:
    """Sem bloco metadata: versão e proveniência são violadas."""
    fm = _fm(ItemKind.COMMAND)
    del fm["metadata"]
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.COMMAND, fm)
    assert {"metadata.version", "metadata.sources"} <= set(_campos(erro))


def test_fontes_repetidas() -> None:
    """Slugs repetidos em metadata.sources são violação."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(
            ItemKind.RULE, _fm(ItemKind.RULE, metadata={"version": "1.0.0", "sources": ["a", "a"]})
        )
    assert "metadata.sources" in _campos(erro)


def test_sem_fonte_e_sem_autoria() -> None:
    """Sem fontes exige authored: true (FR-003)."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.AGENT, _fm(ItemKind.AGENT, metadata={"version": "1.0.0"}))
    assert "metadata.sources" in _campos(erro)


def test_autoral_sem_fonte_aceito() -> None:
    """authored: true dispensa fontes."""
    item = _montar(
        ItemKind.AGENT, _fm(ItemKind.AGENT, metadata={"version": "1.0.0", "authored": True})
    )
    assert item.authored is True
    assert item.sources == ()


@pytest.mark.parametrize("campo", ["authored", "rewrite_pending"])
def test_booleanos_invalidos(campo: str) -> None:
    """authored e rewrite_pending precisam ser booleanos."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.SKILL, _fm(ItemKind.SKILL, metadata={**META, campo: "sim"}))
    assert f"metadata.{campo}" in _campos(erro)


def test_rewrite_pending_informativo() -> None:
    """rewrite_pending: true não invalida o item (FR-024a)."""
    item = _montar(ItemKind.SKILL, _fm(ItemKind.SKILL, metadata={**META, "rewrite_pending": True}))
    assert item.rewrite_pending is True


# --- nome ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind", [ItemKind.SKILL, ItemKind.AGENT, ItemKind.HOOK, ItemKind.REFERENCE]
)
def test_nome_do_frontmatter_diferente_da_entrada(kind: ItemKind) -> None:
    """Nos tipos com name no frontmatter, ele deve ser igual à pasta/arquivo (FR-004)."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(kind, _fm(kind, name="outro"))
    assert "name" in _campos(erro)


@pytest.mark.parametrize("kind", [ItemKind.COMMAND, ItemKind.RULE])
def test_nome_do_arquivo_fora_do_formato(kind: ItemKind) -> None:
    """Command e rule tiram o nome do arquivo, que precisa estar no formato."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(kind, _fm(kind), entry="Revisar_Codigo")
    assert "name" in _campos(erro)


# --- referências e arquivos de apoio --------------------------------------------------------


def test_skill_com_arquivo_de_apoio_ausente() -> None:
    """Link local inexistente numa skill é violação (FR-006)."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.SKILL, _fm(ItemKind.SKILL), refs=("ref/a.md",), missing=("ref/a.md",))
    assert "references" in _campos(erro)


@pytest.mark.parametrize("ref", ["../fora.md", "/abs.md", "file:x.md"])
def test_skill_com_referencia_que_escapa(ref: str) -> None:
    """Link que sai da pasta do item é violação."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.SKILL, _fm(ItemKind.SKILL), refs=(ref,))
    assert "references" in _campos(erro)


@pytest.mark.parametrize(
    "kind", [ItemKind.COMMAND, ItemKind.AGENT, ItemKind.RULE, ItemKind.REFERENCE]
)
def test_arquivo_unico_nao_cita_arquivos_locais(kind: ItemKind) -> None:
    """Tipos de arquivo único não podem citar arquivos locais (não iriam na publicação)."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(kind, _fm(kind), refs=("apoio.md",))
    assert "references" in _campos(erro)


def test_references_citadas_pela_skill() -> None:
    """Skill pode citar references por nome (R3)."""
    fm = _fm(ItemKind.SKILL, metadata={**META, "references": ["checklist-seguranca"]})
    assert _montar(ItemKind.SKILL, fm).references == ("checklist-seguranca",)


@pytest.mark.parametrize(
    "kind", [ItemKind.COMMAND, ItemKind.AGENT, ItemKind.RULE, ItemKind.HOOK, ItemKind.REFERENCE]
)
def test_references_fora_de_skill(kind: ItemKind) -> None:
    """Só skills citam references nesta feature (R3)."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(kind, _fm(kind, metadata={**META, "references": ["x"]}))
    assert "metadata.references" in _campos(erro)


@pytest.mark.parametrize("refs", [["Invalida"], ["a", "a"], "texto"])
def test_references_invalidas(refs: object) -> None:
    """metadata.references precisa ser lista de nomes válidos e únicos."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.SKILL, _fm(ItemKind.SKILL, metadata={**META, "references": refs}))
    assert "metadata.references" in _campos(erro)


# --- hook ----------------------------------------------------------------------------------


def test_hook_valido() -> None:
    """Hook guarda evento, matcher e arquivos executados."""
    fm = _fm(ItemKind.HOOK, event="PostToolUse", matcher="Edit|Write", run=["fmt.sh"])
    item = _montar(ItemKind.HOOK, fm)
    assert (item.hook_event, item.hook_matcher, item.hook_run) == (
        "PostToolUse",
        "Edit|Write",
        ("fmt.sh",),
    )


@pytest.mark.parametrize("evento", [None, "OnSave", ""])
def test_hook_evento_invalido(evento: object) -> None:
    """Evento ausente ou fora da lista do Claude Code é violação (FR-005)."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.HOOK, _fm(ItemKind.HOOK, event=evento))
    assert "event" in _campos(erro)


@pytest.mark.parametrize("run", [None, [], "run.sh", [""], ["../x.sh"]])
def test_hook_run_invalido(run: object) -> None:
    """run precisa ser lista não vazia de arquivos dentro da pasta."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.HOOK, _fm(ItemKind.HOOK, run=run))
    assert "run" in _campos(erro)


def test_hook_run_ausente_no_disco() -> None:
    """Arquivo do run que não existe é violação (FR-005)."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.HOOK, _fm(ItemKind.HOOK), missing=("run.sh",))
    assert "run" in _campos(erro)


def test_hook_matcher_vazio() -> None:
    """matcher, quando presente, não pode ser vazio."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.HOOK, _fm(ItemKind.HOOK, matcher=""))
    assert "matcher" in _campos(erro)


# --- rule ----------------------------------------------------------------------------------


def test_rule_paths() -> None:
    """Rule guarda os globs de paths quando informados."""
    item = _montar(ItemKind.RULE, _fm(ItemKind.RULE, paths=["src/**"]))
    assert item.rule_paths == ("src/**",)


@pytest.mark.parametrize("paths", [[], "src/**", [""]])
def test_rule_paths_invalido(paths: object) -> None:
    """paths precisa ser lista não vazia de globs."""
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.RULE, _fm(ItemKind.RULE, paths=paths))
    assert "paths" in _campos(erro)


# --- coleta de todas as violações ---------------------------------------------------------------


def test_coleta_todas_as_violacoes() -> None:
    """Todas as violações vêm de uma vez, com tipo e nome no erro."""
    fm = {"name": "outro", "description": "", "event": "X", "run": [], "metadata": {"version": "1"}}
    with pytest.raises(InvalidLibraryItemError) as erro:
        _montar(ItemKind.HOOK, fm)
    assert {"name", "description", "event", "run", "metadata.version", "metadata.sources"} <= set(
        _campos(erro)
    )
    assert erro.value.kind == "hook"
    assert erro.value.name == "item-a"
