# -*- coding: utf-8 -*-
"""
NOME: test_validate_skills.py
TITULO: Testes de falha — caso de uso validate_skills (forma + proveniência, em lote)
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.validate_skills
HISTÓRICO:
    - 24/09/2026 16:54: criação (T013, feature 008)
STATUS: DEV
"""

from collections.abc import Mapping
from pathlib import Path

from praxisforge.application.errors import ContractValidationError, SkillNotFoundError
from praxisforge.application.ports import (
    ContractValidator,
    SkillDocument,
    SkillRepository,
    SourceReader,
)
from praxisforge.application.validate_skills import SkillValidationReport, validate_skills
from praxisforge.domain.errors import Violation


class _FakeRepo(SkillRepository):
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


class _FakeReader(SourceReader):
    def __init__(self, documentos: Mapping[Path, dict[str, object]]) -> None:
        self._documentos = documentos
        self.leituras = 0

    def read(self, path: Path) -> dict[str, object]:
        self.leituras += 1
        return dict(self._documentos[path])


class _FakeValidator(ContractValidator):
    def validate(self, document: Mapping[str, object], schema_name: str) -> None:
        if document.get("_invalido"):
            raise ContractValidationError([Violation(field="metadata.extra", reason="inválido")])


def _doc(
    nome: str, *, sources: list[str] | None = None, authored: bool = False, **extra: object
) -> SkillDocument:
    metadata: dict[str, object] = {"version": "1.0.0", "authored": authored}
    if sources is not None:
        metadata["sources"] = sources
    frontmatter: dict[str, object] = {"name": nome, "description": "d", "metadata": metadata}
    frontmatter.update(extra)
    return SkillDocument(
        folder_name=nome, frontmatter=frontmatter, references=[], missing_references=[]
    )


def _fonte(policy: str, **campos: object) -> dict[str, object]:
    documento: dict[str, object] = {
        "schema_version": "2",
        "origin": "https://x.io/repo",
        "author": "Fulano",
        "date": "2026-09-20",
        "license": "MIT",
        "relevance": "r",
        "status": "active",
        "extract_policy": policy,
        "notice_preserved": True,
    }
    documento.update(campos)
    return documento


FONTES = {
    Path("src/data/sources/a/resumo.md"): _fonte("summary"),
    Path("src/data/sources/a/link.md"): _fonte("link"),
    Path("src/data/sources/a/dup.md"): _fonte("summary"),
    Path("src/data/sources/b/dup.md"): _fonte("summary"),
    Path("src/data/sources/a/ruim.md"): _fonte("verbatim", license="Elastic-2.0"),
}


def _validar(
    repo: SkillRepository, names: list[str] | None = None, reader: SourceReader | None = None
) -> SkillValidationReport:
    return validate_skills(
        repo, _FakeValidator(), reader or _FakeReader(FONTES), list(FONTES), names
    )


def _motivos(report: SkillValidationReport, nome: str) -> str:
    return " | ".join(r for f in report.failures if f.name == nome for r in f.reasons)


def test_fonte_citada_inexistente() -> None:
    """Slug sem registro de fonte é falha (FR-006)."""
    report = _validar(_FakeRepo({"s": _doc("s", sources=["nada"])}))
    assert "nada" in _motivos(report, "s") and "não encontrada" in _motivos(report, "s")


def test_slug_ambiguo() -> None:
    """Slug presente em duas categorias é falha."""
    report = _validar(_FakeRepo({"s": _doc("s", sources=["dup"])}))
    assert "ambíguo" in _motivos(report, "s")


def test_fonte_invalida() -> None:
    """Fonte citada que falha na validação de fontes (política acima da licença) é falha."""
    report = _validar(_FakeRepo({"s": _doc("s", sources=["ruim"])}))
    assert "ruim" in _motivos(report, "s") and "inválida" in _motivos(report, "s")


def test_so_fontes_link_e_nao_autoral() -> None:
    """Skill não autoral cujas fontes são todas link falha (FR-007a)."""
    report = _validar(_FakeRepo({"s": _doc("s", sources=["link"])}))
    assert "summary" in _motivos(report, "s") and "verbatim" in _motivos(report, "s")


def test_summary_mais_link_ok() -> None:
    """Uma fonte summary basta; link complementar é aceita."""
    report = _validar(_FakeRepo({"s": _doc("s", sources=["resumo", "link"])}))
    assert [skill.name for skill in report.ok] == ["s"] and report.failures == []


def test_autoral_sem_fontes_ok() -> None:
    """Skill autoral sem fontes é válida."""
    report = _validar(_FakeRepo({"s": _doc("s", authored=True)}))
    assert [skill.name for skill in report.ok] == ["s"]


def test_autoral_com_fonte_link_ok() -> None:
    """Skill autoral pode citar só fontes link (FR-007a não se aplica)."""
    report = _validar(_FakeRepo({"s": _doc("s", sources=["link"], authored=True)}))
    assert report.failures == []


def test_referencia_ausente() -> None:
    """Arquivo referenciado ausente é falha da skill (FR-005)."""
    documento = SkillDocument(
        folder_name="s",
        frontmatter=_doc("s", authored=True).frontmatter,
        references=["ref/a.md"],
        missing_references=["ref/a.md"],
    )
    report = _validar(_FakeRepo({"s": documento}))
    assert "ref/a.md" in _motivos(report, "s")


def test_violacao_de_schema_agregada() -> None:
    """Violação apontada só pelo contrato entra nos motivos da skill."""
    report = _validar(_FakeRepo({"s": _doc("s", authored=True, _invalido=True)}))
    assert "metadata.extra" in _motivos(report, "s")


def test_lote_agrega_por_skill_sem_interromper() -> None:
    """Válidas e inválidas no mesmo lote; cada falha cita a skill (FR-008)."""
    repo = _FakeRepo(
        {
            "a": _doc("a", authored=True),
            "b": _doc("b", sources=["nada"]),
            "c": _doc("c", sources=["resumo"]),
            "d": _doc("outro-nome", authored=True),
        }
    )
    report = _validar(repo)
    assert [skill.name for skill in report.ok] == ["a", "c"]
    assert [f.name for f in report.failures] == ["b", "d"]
    assert all(f.error_type == "InvalidSkillError" for f in report.failures)


def test_all_sem_skills() -> None:
    """--all sem skills devolve relatório vazio."""
    report = _validar(_FakeRepo({}))
    assert report.ok == [] and report.failures == []


def test_nome_inexistente() -> None:
    """Nome pedido que não existe é falha do item, não exceção."""
    report = _validar(_FakeRepo({"a": _doc("a", authored=True)}), names=["nada", "a"])
    assert [skill.name for skill in report.ok] == ["a"]
    assert report.failures[0].name == "nada"
    assert report.failures[0].error_type == "SkillNotFoundError"


def test_fonte_lida_uma_vez_por_lote() -> None:
    """A mesma fonte citada por várias skills é validada uma única vez (escala)."""
    reader = _FakeReader(FONTES)
    repo = _FakeRepo({n: _doc(n, sources=["resumo"]) for n in ("a", "b", "c")})
    _validar(repo, reader=reader)
    assert reader.leituras <= 2
