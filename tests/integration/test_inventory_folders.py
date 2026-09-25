# -*- coding: utf-8 -*-
"""
NOME: test_inventory_folders.py
TITULO: Testes de falha — caso de uso de inventário de curadoria (feature 010)
DATA: 25/09/2026 15:05
MODIFICADO: 25/09/2026 14:53
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.inventory_folders
HISTÓRICO:
    - 25/09/2026 15:05: criação (T014, T029, T030, T034, feature 010)
STATUS: DEV
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from praxisforge.application.inventory_folders import (
    InventoryReport,
    InventoryResult,
    inventory_all,
    inventory_folder,
)
from praxisforge.domain.curation_artifact import Stage
from praxisforge.domain.errors import (
    ConventionsMissingError,
    CurationLockedError,
    CurationStateCorruptError,
    FolderNotFoundError,
    FolderPathInvalidError,
)
from praxisforge.infrastructure.filesystem_folder_locator import FilesystemFolderLocator
from praxisforge.infrastructure.filesystem_folder_walker import FilesystemFolderWalker
from praxisforge.infrastructure.json_curation_store import JsonCurationStore
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.yaml_conventions_loader import YamlConventionsSource
from praxisforge.infrastructure.yaml_folder_registry import YamlFolderRegistryRepository
from praxisforge.presentation.cli import main

ROOT = Path(__file__).parents[2]
AGORA = datetime(2026, 9, 25, 15, 5, tzinfo=ZoneInfo("America/Sao_Paulo"))
_VALIDATOR = JsonSchemaContractValidator(schemas_dir=ROOT / "schemas")

AGENT_SKILLS = {
    "skills/tdd/SKILL.md": "# tdd",
    "skills/tdd/references/apoio.md": "apoio",
    "skills/tdd/CLAUDE.md": "interno da skill",
    ".claude/skills/local/SKILL.md": "# local",
    ".claude/commands/review.md": "cmd",
    ".claude/commands/sub/deploy.md": "cmd",
    "agents/revisor.md": "agent",
    ".claude/agents/outro.md": "agent",
    "hooks/hooks.json": "{}",
    "hooks/scripts/pre.sh": "echo",
    ".claude/rules/py.md": "rule",
    "references/guia.md": "ref",
    "CLAUDE.md": "projeto",
    "AGENTS.md": "agentes",
    "README.md": "leia",
    "docs/x.md": "doc",
    "app.py": "print()",
    "node_modules/a.js": "x",
    "graphify-out/g.json": "{}",
    "logo.png": b"\x89PNG\x00",
    "grande.md": b"a" * 262_145,
}


def _escrever(raiz: Path, arquivos: dict[str, str | bytes]) -> None:
    for rel, conteudo in arquivos.items():
        alvo = raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(conteudo if isinstance(conteudo, bytes) else conteudo.encode())


class _Ambiente:
    """Registro isolado + convenções + store, compostos como na CLI."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.registry = base / "cfg" / "folders.yaml"
        self.registry.parent.mkdir(parents=True)
        shutil.copy(
            ROOT / "src/data/curation-conventions.example.yaml",
            self.registry.parent / "curation-conventions.yaml",
        )
        self.store = JsonCurationStore(self.registry.parent / "curation", _VALIDATOR)

    def registrar(
        self, alias: str, arquivos: dict[str, str | bytes], status: str = "scanned"
    ) -> Path:
        pasta = self.base / "pastas" / alias
        pasta.mkdir(parents=True, exist_ok=True)
        _escrever(pasta, arquivos)
        licenca = "unknown" if status == "pending" else "MIT"
        codigo = main(
            [
                "--registry", str(self.registry), "folders", "add", "--alias", alias,
                "--description", "d", "--content-type", "skills", "--license", licenca,
                "--status", status, "--path", str(pasta),
            ]
        )  # fmt: skip
        assert codigo == 0
        return pasta

    def _deps(self) -> dict[str, object]:
        return {
            "repository": YamlFolderRegistryRepository(self.registry, _VALIDATOR),
            "locator": FilesystemFolderLocator(),
            "walker": FilesystemFolderWalker(),
            "conventions": YamlConventionsSource(
                self.registry.parent / "curation-conventions.yaml", _VALIDATOR
            ),
            "store": self.store,
        }

    def inventariar(self, alias: str) -> InventoryResult:
        return inventory_folder(**self._deps(), alias=alias, now=AGORA)  # type: ignore[arg-type]

    def inventariar_todas(self) -> InventoryReport:
        return inventory_all(**self._deps(), now=AGORA)  # type: ignore[arg-type]

    def manifesto(self, alias: str) -> dict[str, object]:
        return json.loads((self.store_dir(alias) / "manifest.json").read_text("utf-8"))  # type: ignore[no-any-return]

    def estado(self, alias: str) -> dict[str, dict[str, object]]:
        doc = json.loads((self.store_dir(alias) / "state.json").read_text("utf-8"))
        return doc["artifacts"]  # type: ignore[no-any-return]

    def store_dir(self, alias: str) -> Path:
        return self.registry.parent / "curation" / alias


@pytest.fixture
def amb(tmp_path: Path) -> _Ambiente:
    return _Ambiente(tmp_path)


# --- US1 ---------------------------------------------------------------------------


def test_agent_skills_classificado_por_completo(amb: _Ambiente) -> None:
    """SC-001: todos os tipos aparecem com o tipo certo; apoio da skill não vira artefato."""
    amb.registrar("agent_skills", AGENT_SKILLS)
    resultado = amb.inventariar("agent_skills")
    tipos = {a["path"]: a["kind"] for a in amb.manifesto("agent_skills")["artifacts"]}  # type: ignore[index, union-attr]
    assert tipos == {
        "skills/tdd": "skill",
        ".claude/skills/local": "skill",
        ".claude/commands/review.md": "command",
        ".claude/commands/sub/deploy.md": "command",
        "agents/revisor.md": "agent",
        ".claude/agents/outro.md": "agent",
        "hooks": "hook",
        ".claude/rules/py.md": "rule",
        "references/guia.md": "reference",
        "CLAUDE.md": "project_instruction",
        "AGENTS.md": "project_instruction",
        "README.md": "unknown",
        "docs/x.md": "unknown",
    }
    excluidos = {e["path"]: e["reason"] for e in amb.manifesto("agent_skills")["excluded"]}  # type: ignore[index, union-attr]
    assert excluidos == {
        "app.py": "uncurated",
        "node_modules": "fixed_dir",
        "graphify-out": "fixed_dir",
        "logo.png": "binary",
        "grande.md": "too_large",
    }
    skill = next(a for a in amb.manifesto("agent_skills")["artifacts"] if a["path"] == "skills/tdd")  # type: ignore[union-attr, index]
    assert skill["files"] == 3
    assert resultado.artifacts == 13
    assert resultado.pending == 13
    assert resultado.excluded == 5


def test_todo_arquivo_coberto_uma_vez(amb: _Ambiente) -> None:
    """SC-002: cada arquivo está em exatamente um artefato ou sob uma exclusão."""
    pasta = amb.registrar("agent_skills", AGENT_SKILLS)
    amb.inventariar("agent_skills")
    doc = amb.manifesto("agent_skills")
    raizes = [a["path"] for a in doc["artifacts"]] + [e["path"] for e in doc["excluded"]]  # type: ignore[union-attr, index]
    for arquivo in (p for p in pasta.rglob("*") if p.is_file()):
        rel = arquivo.relative_to(pasta).as_posix()
        donos = [r for r in raizes if rel == r or rel.startswith(f"{r}/")]
        assert len(donos) == 1, rel


def test_deterministico(amb: _Ambiente) -> None:
    """SC-003."""
    amb.registrar("agent_skills", AGENT_SKILLS)
    amb.inventariar("agent_skills")
    primeiro = (amb.store_dir("agent_skills") / "manifest.json").read_bytes()
    amb.inventariar("agent_skills")
    assert (amb.store_dir("agent_skills") / "manifest.json").read_bytes() == primeiro


def test_pasta_vazia(amb: _Ambiente) -> None:
    amb.registrar("vazia", {})
    resultado = amb.inventariar("vazia")
    assert (resultado.artifacts, resultado.excluded) == (0, 0)


def test_pasta_pending_e_inventariada(amb: _Ambiente) -> None:
    amb.registrar("licenca_x", {"README.md": "x"}, status="pending")
    assert amb.inventariar("licenca_x").artifacts == 1


def test_alias_inexistente(amb: _Ambiente) -> None:
    amb.registrar("demo_a", {})
    with pytest.raises(FolderNotFoundError):
        amb.inventariar("nao_existe")


def test_convencoes_ausentes(amb: _Ambiente) -> None:
    amb.registrar("demo_a", {})
    (amb.registry.parent / "curation-conventions.yaml").unlink()
    with pytest.raises(ConventionsMissingError):
        amb.inventariar("demo_a")


def test_lock_ocupado(amb: _Ambiente) -> None:
    amb.registrar("demo_a", {})
    with JsonCurationStore(amb.registry.parent / "curation", _VALIDATOR).lock("demo_a"):
        with pytest.raises(CurationLockedError):
            amb.inventariar("demo_a")


def test_estado_corrompido_nao_e_sobrescrito(amb: _Ambiente) -> None:
    amb.registrar("demo_a", {"README.md": "x"})
    amb.store_dir("demo_a").mkdir(parents=True)
    (amb.store_dir("demo_a") / "state.json").write_text("{", encoding="utf-8")
    with pytest.raises(CurationStateCorruptError):
        amb.inventariar("demo_a")
    assert (amb.store_dir("demo_a") / "state.json").read_text(encoding="utf-8") == "{"
    assert not (amb.store_dir("demo_a") / "manifest.json").exists()


# --- US3 ---------------------------------------------------------------------------


def _finalizar_tudo(amb: _Ambiente, alias: str) -> None:
    arquivo = amb.store_dir(alias) / "state.json"
    doc = json.loads(arquivo.read_text("utf-8"))
    for artefato in doc["artifacts"].values():
        artefato["stage"] = Stage.PROMOTED.value
    arquivo.write_text(json.dumps(doc), encoding="utf-8")


def test_incremental_so_o_alterado_volta(amb: _Ambiente) -> None:
    """SC-004: alterar 1 arquivo (de apoio da skill) → só a skill volta; sumido → removed."""
    pasta = amb.registrar("agent_skills", AGENT_SKILLS)
    amb.inventariar("agent_skills")
    _finalizar_tudo(amb, "agent_skills")
    (pasta / "skills/tdd/references/apoio.md").write_text("mudou", encoding="utf-8")
    (pasta / "README.md").unlink()
    (pasta / "novo.md").write_text("novo", encoding="utf-8")
    resultado = amb.inventariar("agent_skills")
    etapas = {p: s["stage"] for p, s in amb.estado("agent_skills").items()}
    assert etapas.pop("skills/tdd") == "pending"
    assert etapas.pop("README.md") == "removed"
    assert etapas.pop("novo.md") == "pending"
    assert set(etapas.values()) == {"promoted"}
    assert (resultado.pending, resultado.removed) == (2, 1)


def test_pasta_inacessivel_mantem_estado(amb: _Ambiente) -> None:
    pasta = amb.registrar("demo_a", {"README.md": "x"})
    amb.inventariar("demo_a")
    antes = (amb.store_dir("demo_a") / "state.json").read_bytes()
    shutil.rmtree(pasta)
    with pytest.raises(FolderPathInvalidError):
        amb.inventariar("demo_a")
    assert (amb.store_dir("demo_a") / "state.json").read_bytes() == antes


# --- US4 ---------------------------------------------------------------------------


def test_lote_tolerante(amb: _Ambiente) -> None:
    amb.registrar("ok_a", {"README.md": "a"})
    amb.registrar("ok_b", {"CLAUDE.md": "b"})
    sumida = amb.registrar("sumida_c", {})
    amb.registrar("ignorada_d", {"README.md": "d"}, status="ignore")
    shutil.rmtree(sumida)
    relatorio = amb.inventariar_todas()
    assert [r.alias for r in relatorio.ok] == ["ok_a", "ok_b"]
    assert [f.alias for f in relatorio.failures] == ["sumida_c"]
    assert relatorio.skipped == ["ignorada_d"]
    assert not amb.store_dir("ignorada_d").exists()


def test_lote_lock_ocupado_vira_falha_da_pasta(amb: _Ambiente) -> None:
    amb.registrar("ok_a", {"README.md": "a"})
    amb.registrar("presa_b", {"README.md": "b"})
    with JsonCurationStore(amb.registry.parent / "curation", _VALIDATOR).lock("presa_b"):
        relatorio = amb.inventariar_todas()
    assert [r.alias for r in relatorio.ok] == ["ok_a"]
    assert [(f.alias, f.error_type) for f in relatorio.failures] == [
        ("presa_b", "CurationLockedError")
    ]


def test_lote_sem_convencoes_falha_antes(amb: _Ambiente) -> None:
    amb.registrar("ok_a", {})
    (amb.registry.parent / "curation-conventions.yaml").unlink()
    with pytest.raises(ConventionsMissingError):
        amb.inventariar_todas()


# --- SC-006 ------------------------------------------------------------------------


def test_nada_escrito_na_pasta_nem_no_repositorio(amb: _Ambiente) -> None:
    pasta = amb.registrar("agent_skills", AGENT_SKILLS)
    antes = {p: p.stat().st_mtime_ns for p in pasta.rglob("*")}
    repo_antes = sorted(os.listdir(ROOT))
    amb.inventariar("agent_skills")
    assert {p: p.stat().st_mtime_ns for p in pasta.rglob("*")} == antes
    assert sorted(os.listdir(ROOT)) == repo_antes
