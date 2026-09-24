# -*- coding: utf-8 -*-
"""
NOME: test_build_catalog.py
TITULO: Testes de falha — caso de uso build_catalog (skills/README.md determinístico)
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.build_catalog
HISTÓRICO:
    - 24/09/2026 16:54: criação (T022, feature 008)
STATUS: DEV
"""

from collections.abc import Mapping
from pathlib import Path

from praxisforge.application.build_catalog import build_catalog, render_catalog
from praxisforge.application.ports import (
    CatalogWriter,
    ContractValidator,
    SkillDocument,
    SkillRepository,
    SourceReader,
)
from praxisforge.domain.errors import SkillNotFoundError
from praxisforge.domain.skill import Skill


def _skill(nome: str, **campos: object) -> Skill:
    base: dict[str, object] = {
        "name": nome,
        "description": f"Propósito de {nome}",
        "version": "1.0.0",
        "sources": (),
        "authored": True,
        "license": None,
        "references": (),
    }
    base.update(campos)
    return Skill(**base)  # type: ignore[arg-type]


def test_render_cabecalho_fixo_e_tabela_ordenada() -> None:
    """Cabeçalho 'gerado — não editar' e linhas em ordem alfabética."""
    conteudo = render_catalog([_skill("zeta"), _skill("alfa")])
    assert "gerado" in conteudo and "não editar" in conteudo
    assert "| Skill | Propósito | Versão | Caminho | Fontes |" in conteudo
    assert conteudo.index("| alfa |") < conteudo.index("| zeta |")
    assert "`skills/alfa/`" in conteudo


def test_render_normaliza_descricao() -> None:
    """Quebras de linha viram espaço e `|` é escapado."""
    conteudo = render_catalog([_skill("a", description="linha 1\nlinha 2 | x")])
    assert "linha 1 linha 2 \\| x" in conteudo


def test_render_fontes_ordenadas_ou_autoral() -> None:
    """Fontes em ordem alfabética; sem fontes → 'autoral'."""
    conteudo = render_catalog([_skill("a", sources=("zz", "aa"), authored=False), _skill("b")])
    assert "| aa, zz |" in conteudo
    assert "| autoral |" in conteudo


def test_render_sem_skills() -> None:
    """Sem skills → mensagem 'nenhuma skill'."""
    assert "nenhuma skill" in render_catalog([]).lower()


def test_render_deterministico_e_sem_data() -> None:
    """Mesma entrada → mesma saída; nenhum 'Criado em'/'Modificado em'."""
    skills = [_skill("a"), _skill("b")]
    assert render_catalog(skills) == render_catalog(list(reversed(skills)))
    assert "Modificado em" not in render_catalog(skills)


class _Repo(SkillRepository):
    def __init__(self, documentos: Mapping[str, SkillDocument]) -> None:
        self._documentos = documentos

    def list_names(self) -> list[str]:
        return sorted(self._documentos)

    def load(self, name: str) -> SkillDocument:
        if name not in self._documentos:
            raise SkillNotFoundError(name)
        return self._documentos[name]

    def content_hash(self, name: str) -> str:
        return "0" * 64

    def skill_dir(self, name: str) -> Path:
        return Path("skills") / name


class _Validator(ContractValidator):
    def validate(self, document: Mapping[str, object], schema_name: str) -> None:
        return None


class _Reader(SourceReader):
    def read(self, path: Path) -> dict[str, object]:
        raise AssertionError("sem fontes neste teste")


class _Writer(CatalogWriter):
    def __init__(self) -> None:
        self.conteudos: list[str] = []

    def write(self, content: str) -> None:
        self.conteudos.append(content)


def _doc(nome: str, versao: str = "1.0.0") -> SkillDocument:
    return SkillDocument(
        folder_name=nome,
        frontmatter={
            "name": nome,
            "description": "d",
            "metadata": {"version": versao, "authored": True},
        },
        references=[],
        missing_references=[],
    )


def test_build_omite_invalidas_e_lista_no_resultado() -> None:
    """Inválidas ficam fora do catálogo e aparecem em omitted."""
    writer = _Writer()
    resultado = build_catalog(
        _Repo({"boa": _doc("boa"), "ruim": _doc("ruim", "1")}), _Validator(), _Reader(), [], writer
    )
    assert resultado.skills == ["boa"]
    assert [f.name for f in resultado.omitted] == ["ruim"]
    assert "| boa |" in writer.conteudos[0] and "ruim" not in writer.conteudos[0]


def test_build_sem_skills_grava_catalogo_vazio() -> None:
    """Sem skills o catálogo é gravado com a mensagem de vazio."""
    writer = _Writer()
    resultado = build_catalog(_Repo({}), _Validator(), _Reader(), [], writer)
    assert resultado.skills == [] and resultado.omitted == []
    assert "nenhuma skill" in writer.conteudos[0].lower()
