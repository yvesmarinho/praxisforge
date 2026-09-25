# -*- coding: utf-8 -*-
"""
NOME: test_validate_library.py
TITULO: Testes de falha — caso de uso validate_library (forma por tipo + proveniência)
DATA: 25/09/2026 13:08
MODIFICADO: 25/09/2026 13:08
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.validate_library
HISTÓRICO:
    - 25/09/2026 13:08: criação (T016, feature 009) — sucede test_validate_skills.py
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.application.validate_library import LibraryValidationReport, validate_library
from praxisforge.domain.errors import LibraryNotFoundError
from praxisforge.domain.library_item import ItemKind
from praxisforge.infrastructure.filesystem_library_repository import FilesystemLibraryRepository
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.source_frontmatter import FrontmatterSourceReader
from tests.library_helpers import criar_projeto, escrever_fonte, escrever_item


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return criar_projeto(tmp_path / "projeto")


def _validar(
    root: Path, kind: ItemKind | None = None, name: str | None = None
) -> LibraryValidationReport:
    fontes = sorted((root / "src" / "data" / "sources").rglob("*.md"))
    return validate_library(
        FilesystemLibraryRepository(root / "library"),
        JsonSchemaContractValidator(schemas_dir=root / "schemas"),
        FrontmatterSourceReader(),
        fontes,
        kind=kind,
        name=name,
    )


def _motivos(report: LibraryValidationReport, kind: str, name: str) -> str:
    return " | ".join(
        motivo for f in report.failures if (f.kind, f.name) == (kind, name) for motivo in f.reasons
    )


def _ok(report: LibraryValidationReport) -> list[str]:
    return [f"{i.kind.value}/{i.name}" for i in report.ok]


def test_um_item_valido_de_cada_tipo(root: Path) -> None:
    """Seis tipos válidos → seis ok, na ordem dos tipos."""
    for kind in ("skill", "command", "agent", "hook", "rule", "reference"):
        escrever_item(root, kind, f"{kind}-a")
    report = _validar(root)
    assert _ok(report) == [
        "skill/skill-a",
        "command/command-a",
        "agent/agent-a",
        "hook/hook-a",
        "rule/rule-a",
        "reference/reference-a",
    ]
    assert report.failures == []


def test_falha_de_um_nao_interrompe_os_demais(root: Path) -> None:
    """Command sem description falha; os outros continuam válidos (FR-008, SC-005)."""
    escrever_item(root, "skill", "boa")
    (root / "library" / "commands" / "ruim.md").write_text(
        "---\nmetadata:\n  version: '1.0.0'\n  authored: true\n---\n", encoding="utf-8"
    )
    escrever_item(root, "rule", "tambem-boa")
    report = _validar(root)
    assert _ok(report) == ["skill/boa", "rule/tambem-boa"]
    assert "description" in _motivos(report, "command", "ruim")


def test_fonte_inexistente(root: Path) -> None:
    """Fonte citada que não existe é falha citando o slug (FR-009)."""
    escrever_item(root, "agent", "a", sources=["nada"], authored=None)
    assert "fonte 'nada' não encontrada" in _motivos(_validar(root), "agent", "a")


def test_fonte_duplicada(root: Path) -> None:
    """Slug presente em duas categorias é ambíguo."""
    escrever_fonte(root, "x", "dup")
    escrever_fonte(root, "y", "dup")
    escrever_item(root, "agent", "a", sources=["dup"], authored=None)
    assert "ambíguo" in _motivos(_validar(root), "agent", "a")


def test_fonte_invalida_v2(root: Path) -> None:
    """Fonte no formato antigo é inválida para o item."""
    escrever_fonte(root, "x", "velha", versao="2")
    escrever_item(root, "agent", "a", sources=["velha"], authored=None)
    assert "fonte 'velha' inválida" in _motivos(_validar(root), "agent", "a")


def test_fonte_valida_sustenta_item_nao_autoral(root: Path) -> None:
    """Uma fonte v3 válida basta (FR-009)."""
    escrever_fonte(root, "x", "guia")
    escrever_item(root, "agent", "a", sources=["guia"], authored=None)
    assert _ok(_validar(root)) == ["agent/a"]


def test_reference_citada_inexistente(root: Path) -> None:
    """Skill que cita reference ausente falha."""
    escrever_item(root, "skill", "s", metadata={"references": ["checklist"]})
    assert "reference 'checklist' não encontrada" in _motivos(_validar(root), "skill", "s")


def test_reference_citada_invalida(root: Path) -> None:
    """Skill que cita reference inválida falha citando a reference."""
    (root / "library" / "references" / "checklist.md").write_text(
        "sem frontmatter\n", encoding="utf-8"
    )
    escrever_item(root, "skill", "s", metadata={"references": ["checklist"]})
    assert "reference 'checklist' inválida" in _motivos(_validar(root), "skill", "s")


def test_reference_citada_valida(root: Path) -> None:
    """Reference existente e válida é aceita."""
    escrever_item(root, "reference", "checklist")
    escrever_item(root, "skill", "s", metadata={"references": ["checklist"]})
    assert "skill/s" in _ok(_validar(root))


def test_schema_do_tipo_e_aplicado(root: Path) -> None:
    """Campo fora do contrato do tipo (rule com paths vazio) vira violação."""
    escrever_item(root, "rule", "r", campos={"paths": []})
    assert "paths" in _motivos(_validar(root), "rule", "r")


def test_filtro_por_tipo(root: Path) -> None:
    """Com kind, só os itens daquele tipo são avaliados."""
    escrever_item(root, "skill", "s")
    escrever_item(root, "agent", "a")
    assert _ok(_validar(root, kind=ItemKind.AGENT)) == ["agent/a"]


def test_filtro_por_nome(root: Path) -> None:
    """Com kind e name, só o item é avaliado; inexistente vira falha."""
    escrever_item(root, "agent", "a")
    escrever_item(root, "agent", "b")
    assert _ok(_validar(root, kind=ItemKind.AGENT, name="b")) == ["agent/b"]
    report = _validar(root, kind=ItemKind.AGENT, name="zzz")
    assert "não encontrado" in _motivos(report, "agent", "zzz")


def test_entrada_de_tipo_desconhecido_conta_como_falha(root: Path) -> None:
    """Entrada fora dos tipos é reportada como tipo desconhecido (sem filtro)."""
    (root / "library" / "prompts").mkdir()
    escrever_item(root, "agent", "a")
    report = _validar(root)
    assert _ok(report) == ["agent/a"]
    assert "tipo desconhecido" in _motivos(report, "?", "prompts")
    assert _validar(root, kind=ItemKind.AGENT).failures == []


def test_rewrite_pending_reportado_sem_invalidar(root: Path) -> None:
    """Item com reescrita pendente é válido e listado à parte (FR-024a)."""
    escrever_item(root, "skill", "s", metadata={"rewrite_pending": True})
    report = _validar(root)
    assert _ok(report) == ["skill/s"]
    assert [i.name for i in report.rewrite_pending] == ["s"]


def test_arquivo_ilegivel_vira_falha_do_item(root: Path) -> None:
    """Arquivo ilegível falha só aquele item."""
    (root / "library" / "agents" / "x.md").write_bytes(b"\xff\xfe")
    escrever_item(root, "agent", "a")
    report = _validar(root)
    assert _ok(report) == ["agent/a"]
    assert "ilegível" in _motivos(report, "agent", "x")


def test_acervo_vazio(root: Path) -> None:
    """Acervo sem itens: zero ok, zero falhas."""
    report = _validar(root)
    assert (report.ok, report.failures) == ([], [])


def test_acervo_ausente_propaga(tmp_path: Path) -> None:
    """library/ ausente é erro de ambiente, não falha por item."""
    with pytest.raises(LibraryNotFoundError):
        _validar(tmp_path)
