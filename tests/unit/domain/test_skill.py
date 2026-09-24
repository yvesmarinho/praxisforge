# -*- coding: utf-8 -*-
"""
NOME: test_skill.py
TITULO: Testes de falha — entidade Skill, SkillName e extração de referências (feature 008)
DATA: 24/09/2026 16:40
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.skill
HISTÓRICO:
    - 24/09/2026 16:40: criação (T004, T005, feature 008)
STATUS: DEV
"""

import pytest

from praxisforge.domain.errors import InvalidSkillError
from praxisforge.domain.skill import Skill, SkillName, extract_references


def _fm(**campos: object) -> dict[str, object]:
    documento: dict[str, object] = {
        "name": "revisar-codigo",
        "description": "Revisa código Python",
        "metadata": {"version": "1.0.0", "sources": ["guia-a"]},
    }
    documento.update(campos)
    return documento


def _campos(error: InvalidSkillError) -> list[str]:
    return [v.field for v in error.violations]


# --- SkillName -------------------------------------------------------------------------------


@pytest.mark.parametrize("nome", ["a", "revisar-codigo", "x1-y2", "a" * 64])
def test_skill_name_valido(nome: str) -> None:
    """Nomes minúsculos com hífens, até 64 caracteres."""
    assert SkillName(nome).value == nome


@pytest.mark.parametrize(
    "nome", ["", "Revisar", "revisar codigo", "-x", "x-", "a--b", "a_b", "a" * 65]
)
def test_skill_name_invalido(nome: str) -> None:
    """Nome fora do formato ou >64 caracteres levanta InvalidSkillError no campo name."""
    with pytest.raises(InvalidSkillError) as info:
        SkillName(nome)
    assert _campos(info.value) == ["name"]


# --- Skill.from_parts ------------------------------------------------------------------------


def test_skill_valida_com_fontes() -> None:
    """Skill válida com fontes devolve a entidade com os campos normalizados."""
    skill = Skill.from_parts("revisar-codigo", _fm(license="MIT"), ["ref/guia.md"])
    assert skill.name == "revisar-codigo"
    assert skill.version == "1.0.0"
    assert skill.sources == ("guia-a",)
    assert skill.authored is False
    assert skill.license == "MIT"
    assert skill.references == ("ref/guia.md",)


def test_skill_valida_autoral_sem_fontes() -> None:
    """Skill sem fontes e com authored: true é válida (FR-007)."""
    skill = Skill.from_parts(
        "revisar-codigo", _fm(metadata={"version": "0.1.0", "authored": True}), []
    )
    assert skill.authored is True and skill.sources == ()


def test_nome_diverge_da_pasta() -> None:
    """name diferente do nome da pasta é violação (FR-003)."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts("outra", _fm(), [])
    assert "name" in _campos(info.value)


@pytest.mark.parametrize("nome", ["Revisar", "a" * 65])
def test_nome_fora_do_formato(nome: str) -> None:
    """name fora do formato é violação mesmo quando igual à pasta."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts(nome, _fm(name=nome), [])
    assert "name" in _campos(info.value)


@pytest.mark.parametrize("descricao", ["", "   ", "x" * 1025, None])
def test_descricao_invalida(descricao: object) -> None:
    """description vazia (após strip), >1024 ou ausente é violação (FR-004)."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts("revisar-codigo", _fm(description=descricao), [])
    assert "description" in _campos(info.value)


@pytest.mark.parametrize("versao", ["1", "01.0.0", "1.0.0-", "v1.0.0", "", None])
def test_versao_nao_semver(versao: object) -> None:
    """metadata.version fora do semver 2.0 é violação (FR-002)."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts("revisar-codigo", _fm(metadata={"version": versao, "sources": ["a"]}), [])
    assert "metadata.version" in _campos(info.value)


def test_versao_semver_com_prerelease_e_build() -> None:
    """Semver com pré-release e build é aceito."""
    skill = Skill.from_parts(
        "revisar-codigo", _fm(metadata={"version": "1.0.0-rc.1+build.5", "sources": ["a"]}), []
    )
    assert skill.version == "1.0.0-rc.1+build.5"


def test_metadata_ausente() -> None:
    """Sem metadata não há versão: violação em metadata.version."""
    documento = _fm()
    del documento["metadata"]
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts("revisar-codigo", documento, [])
    assert "metadata.version" in _campos(info.value)


def test_sem_fontes_e_nao_autoral() -> None:
    """Sem fontes e authored falso/ausente é violação (FR-007)."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts("revisar-codigo", _fm(metadata={"version": "1.0.0"}), [])
    assert "metadata.sources" in _campos(info.value)


def test_fontes_repetidas() -> None:
    """Slugs repetidos em metadata.sources são violação."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts(
            "revisar-codigo", _fm(metadata={"version": "1.0.0", "sources": ["a", "a"]}), []
        )
    assert "metadata.sources" in _campos(info.value)


@pytest.mark.parametrize("sources", ["a", [1], [""]])
def test_fontes_com_tipo_invalido(sources: object) -> None:
    """metadata.sources precisa ser lista de slugs não vazios."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts(
            "revisar-codigo", _fm(metadata={"version": "1.0.0", "sources": sources}), []
        )
    assert "metadata.sources" in _campos(info.value)


def test_authored_nao_booleano() -> None:
    """metadata.authored precisa ser booleano."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts(
            "revisar-codigo", _fm(metadata={"version": "1.0.0", "authored": "sim"}), []
        )
    assert "metadata.authored" in _campos(info.value)


@pytest.mark.parametrize("ref", ["../fora.md", "a/../../fora.md", "/etc/x", "file:///etc/x"])
def test_referencia_fora_da_pasta(ref: str) -> None:
    """Referência que sai da pasta, absoluta ou com esquema file: é violação (FR-005)."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts("revisar-codigo", _fm(), [ref])
    assert "references" in _campos(info.value)


def test_referencia_ausente() -> None:
    """Referência inexistente (informada pela infraestrutura) é violação (FR-005)."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts("revisar-codigo", _fm(), ["ref/a.md"], missing_references=["ref/a.md"])
    assert "references" in _campos(info.value)
    assert "ref/a.md" in str(info.value)


def test_todas_as_violacoes_numa_unica_excecao() -> None:
    """Violações de vários campos são coletadas de uma vez."""
    with pytest.raises(InvalidSkillError) as info:
        Skill.from_parts(
            "outra",
            {"name": "Nome Ruim", "description": "", "metadata": {"version": "1"}},
            ["../x.md"],
        )
    assert info.value.name == "outra"
    assert set(_campos(info.value)) >= {
        "name",
        "description",
        "metadata.version",
        "metadata.sources",
        "references",
    }


# --- extract_references ----------------------------------------------------------------------


def test_extract_references_links_e_imagens() -> None:
    """Coleta alvos de links e imagens, em ordem, sem duplicatas."""
    corpo = "Veja [guia](ref/guia.md) e ![fig](img/a.png).\nDe novo [guia](ref/guia.md)."
    assert extract_references(corpo) == ["ref/guia.md", "img/a.png"]


def test_extract_references_ignora_externos_e_ancoras() -> None:
    """Ignora http, https, mailto e âncoras puras; remove #fragmento."""
    corpo = (
        "[a](https://x.io) [b](http://x.io) [c](mailto:a@b.c) [d](#secao) [e](ref/guia.md#passo-2)"
    )
    assert extract_references(corpo) == ["ref/guia.md"]


def test_extract_references_corpo_vazio() -> None:
    """Corpo sem links devolve lista vazia."""
    assert extract_references("") == []


def test_extract_references_ignora_codigo_inline_e_blocos() -> None:
    """Links dentro de `código` ou de blocos cercados são exemplos, não referências (bug T042)."""
    corpo = (
        "Cite por link relativo, ex.: `[exemplo](exemplos/a.md)`.\n"
        "```markdown\n[b](exemplos/b.md)\n```\n"
        "~~~\n[c](exemplos/c.md)\n~~~\n"
        "Real: [d](ref/d.md)\n"
    )
    assert extract_references(corpo) == ["ref/d.md"]
