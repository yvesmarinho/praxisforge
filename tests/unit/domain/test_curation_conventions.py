# -*- coding: utf-8 -*-
"""
NOME: test_curation_conventions.py
TITULO: Testes de falha — convenções de classificação do inventário (feature 010)
DATA: 25/09/2026 15:00
MODIFICADO: 25/09/2026 14:52
VERSÃO: 0.1.0
DEPEND: pytest, pathspec (só como matcher injetado), praxisforge.domain.curation_conventions
HISTÓRICO:
    - 25/09/2026 15:00: criação (T010, feature 010)
STATUS: DEV
"""

import pathspec
import pytest

from praxisforge.domain.curation_artifact import ArtifactKind
from praxisforge.domain.curation_conventions import ConventionRule, Conventions, RuleUnit
from praxisforge.domain.errors import ConventionsError


def _match(pattern: str, path: str) -> bool:
    return pathspec.PathSpec.from_lines("gitignore", [pattern]).match_file(path)


SKILL = ConventionRule(ArtifactKind.SKILL, "**/skills/*", RuleUnit.DIRECTORY, "SKILL.md")
HOOK = ConventionRule(ArtifactKind.HOOK, "**/hooks", RuleUnit.DIRECTORY)
AGENT = ConventionRule(ArtifactKind.AGENT, "**/agents/*.md", RuleUnit.FILE)
CLAUDE = ConventionRule(ArtifactKind.PROJECT_INSTRUCTION, "**/CLAUDE.md", RuleUnit.FILE)


def _conv(*rules: ConventionRule) -> Conventions:
    return Conventions(rules or (SKILL, HOOK, AGENT, CLAUDE), _match)


@pytest.mark.parametrize(
    "args",
    [
        (ArtifactKind.UNKNOWN, "*.md", RuleUnit.FILE, None),
        (ArtifactKind.SKILL, "", RuleUnit.FILE, None),
        (ArtifactKind.SKILL, "  ", RuleUnit.FILE, None),
        (ArtifactKind.SKILL, "x", RuleUnit.DIRECTORY, "a/b"),
        (ArtifactKind.SKILL, "x", RuleUnit.FILE, "SKILL.md"),
    ],
)
def test_regra_invalida(args: tuple[ArtifactKind, str, RuleUnit, str | None]) -> None:
    """kind unknown, pattern vazio, marker com barra ou em regra de arquivo são recusados."""
    with pytest.raises(ConventionsError):
        ConventionRule(*args)


def test_sem_regras_recusado() -> None:
    with pytest.raises(ConventionsError):
        Conventions((), _match)


@pytest.mark.parametrize("diretorio", ["skills/x", ".claude/skills/x", "plugin/skills/y"])
def test_skill_exige_marker(diretorio: str) -> None:
    conv = _conv()
    assert conv.classify_directory(diretorio, frozenset({"SKILL.md"})) is ArtifactKind.SKILL
    assert conv.classify_directory(diretorio, frozenset({"README.md"})) is None


def test_hook_diretorio_sem_marker() -> None:
    conv = _conv()
    assert conv.classify_directory("hooks", frozenset()) is ArtifactKind.HOOK
    assert conv.classify_directory(".claude/hooks", frozenset({"a.sh"})) is ArtifactKind.HOOK


def test_regra_de_arquivo_nao_classifica_diretorio() -> None:
    assert _conv().classify_directory("agents", frozenset({"a.md"})) is None


def test_arquivos() -> None:
    conv = _conv()
    assert conv.classify_file("agents/a.md") is ArtifactKind.AGENT
    assert conv.classify_file(".claude/agents/a.md") is ArtifactKind.AGENT
    assert conv.classify_file("sub/dir/CLAUDE.md") is ArtifactKind.PROJECT_INSTRUCTION
    assert conv.classify_file("README.md") is None
    assert conv.classify_file("hooks") is None  # regra de diretório não casa arquivo


def test_prioridade_pela_ordem() -> None:
    primeiro = ConventionRule(ArtifactKind.RULE, "**/agents/*.md", RuleUnit.FILE)
    assert _conv(primeiro, AGENT).classify_file("agents/a.md") is ArtifactKind.RULE
    assert _conv(AGENT, primeiro).classify_file("agents/a.md") is ArtifactKind.AGENT


def test_versao_estavel_e_sensivel_a_regras() -> None:
    """Mesmas regras → mesma versão; regra diferente → versão diferente (FR-016)."""
    assert _conv().version == _conv().version
    assert len(_conv().version) == 64
    assert _conv(SKILL, HOOK).version != _conv(SKILL, HOOK, AGENT).version
    assert _conv(AGENT, CLAUDE).version != _conv(CLAUDE, AGENT).version
