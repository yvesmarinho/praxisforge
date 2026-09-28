# -*- coding: utf-8 -*-
"""
NOME: triage_helpers.py
TITULO: Ambiente de teste da triagem: registro, pasta inventariada, acervo e prompts isolados
DATA: 28/09/2026 15:59
MODIFICADO: 28/09/2026 15:59
VERSÃO: 0.1.0
DEPEND: praxisforge (application, infrastructure), tests.library_helpers
HISTÓRICO:
    - 28/09/2026 15:59: criação (T024, feature 011)
STATUS: DEV
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from praxisforge.application.inventory_folders import inventory_folder
from praxisforge.application.triage_folders import TriageDeps, TriageOptions, TriageReport, triage
from praxisforge.infrastructure.filesystem_artifact_reader import FilesystemArtifactReader
from praxisforge.infrastructure.filesystem_folder_locator import FilesystemFolderLocator
from praxisforge.infrastructure.filesystem_folder_walker import FilesystemFolderWalker
from praxisforge.infrastructure.filesystem_prompt_source import FilesystemPromptSource
from praxisforge.infrastructure.json_curation_store import JsonCurationStore
from praxisforge.infrastructure.json_draft_store import JsonDraftStore
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from praxisforge.infrastructure.library_catalog import FilesystemLibraryCatalog
from praxisforge.infrastructure.yaml_conventions_loader import YamlConventionsSource
from praxisforge.infrastructure.yaml_folder_registry import YamlFolderRegistryRepository
from praxisforge.presentation.cli import main
from tests.fakes.fake_language_model import FakeLanguageModel
from tests.library_helpers import REPO_ROOT, criar_projeto

AGORA = datetime(2026, 9, 28, 15, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
VALIDATOR = JsonSchemaContractValidator(schemas_dir=REPO_ROOT / "schemas")


class TriageEnv:
    """Registro + pastas + acervo (projeto temporário) + prompts, compostos como na CLI."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self.registry = base / "cfg" / "folders.yaml"
        self.registry.parent.mkdir(parents=True)
        shutil.copy(
            REPO_ROOT / "src/data/curation-conventions.example.yaml",
            self.registry.parent / "curation-conventions.yaml",
        )
        self.project = criar_projeto(base / "projeto")
        shutil.copytree(REPO_ROOT / "prompts", self.project / "prompts")
        (self.project / "library" / "INDEX.md").write_text("# Índice\n", encoding="utf-8")
        self.store = JsonCurationStore(self.registry.parent / "curation", VALIDATOR)
        self.drafts = JsonDraftStore(self.registry.parent / "curation", VALIDATOR)
        self.model = FakeLanguageModel()

    def folder(self, alias: str) -> Path:
        return self.base / "pastas" / alias

    def registrar(
        self,
        alias: str,
        arquivos: dict[str, str],
        license: str = "MIT",  # noqa: A002 - nome do campo do registro
        status: str = "scanned",
        inventariar: bool = True,
    ) -> Path:
        pasta = self.folder(alias)
        pasta.mkdir(parents=True, exist_ok=True)
        self.escrever(alias, arquivos)
        codigo = main(
            [
                "--registry", str(self.registry), "folders", "add", "--alias", alias,
                "--description", "d", "--content-type", "skills", "--license", license,
                "--status", status, "--path", str(pasta),
            ]
        )  # fmt: skip
        assert codigo == 0
        if inventariar:
            self.inventariar(alias)
        return pasta

    def escrever(self, alias: str, arquivos: dict[str, str]) -> None:
        for rel, conteudo in arquivos.items():
            alvo = self.folder(alias) / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(conteudo, encoding="utf-8")

    def inventariar(self, alias: str) -> None:
        inventory_folder(
            repository=YamlFolderRegistryRepository(self.registry, VALIDATOR),
            locator=FilesystemFolderLocator(),
            walker=FilesystemFolderWalker(),
            conventions=YamlConventionsSource(
                self.registry.parent / "curation-conventions.yaml", VALIDATOR
            ),
            store=self.store,
            alias=alias,
            now=AGORA,
        )

    def deps(self) -> TriageDeps:
        return TriageDeps(
            repository=YamlFolderRegistryRepository(self.registry, VALIDATOR),
            locator=FilesystemFolderLocator(),
            store=self.store,
            model=self.model,
            prompts=FilesystemPromptSource(self.project / "prompts" / "curation"),
            catalog=FilesystemLibraryCatalog(self.project / "library"),
            reader=FilesystemArtifactReader(),
            drafts=self.drafts,
        )

    def triar(self, alias: str | None, **opcoes: Any) -> TriageReport:
        return triage(self.deps(), alias, TriageOptions(**opcoes), now=lambda: AGORA)

    def estado(self, alias: str) -> dict[str, dict[str, Any]]:
        documento = json.loads(
            (self.registry.parent / "curation" / alias / "state.json").read_text("utf-8")
        )
        return documento["artifacts"]  # type: ignore[no-any-return]


def triagem(verdict: str = "out_of_scope", **campos: Any) -> dict[str, Any]:
    """Resposta de triagem válida pelo schema, com campos sobrescritos."""
    base: dict[str, Any] = {
        "verdict": verdict,
        "justification": f"justificativa {verdict}",
        "covered_by": [],
        "merge_target": None,
        "suggested_kind": None,
        "ideas_summary": None,
    }
    return base | campos
