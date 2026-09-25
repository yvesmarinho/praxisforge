# -*- coding: utf-8 -*-
"""
NOME: test_curation_artifact.py
TITULO: Testes de falha — entidades do inventário de curadoria (feature 010)
DATA: 25/09/2026 14:52
MODIFICADO: 25/09/2026 14:50
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.domain.curation_artifact
HISTÓRICO:
    - 25/09/2026 14:52: criação (T006, feature 010)
STATUS: DEV
"""

import pytest

from praxisforge.domain.curation_artifact import (
    Artifact,
    ArtifactKind,
    ExcludedEntry,
    ExclusionReason,
    Manifest,
    Stage,
    is_final,
)
from praxisforge.domain.errors import InvalidCurationArtifactError, PraxisForgeError

SHA = "b" * 64


def _artefato(**campos: object) -> Artifact:
    base: dict[str, object] = {
        "path": "skills/x",
        "kind": ArtifactKind.SKILL,
        "size": 10,
        "sha256": SHA,
        "files": 1,
    }
    base.update(campos)
    return Artifact(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize("enum", [ArtifactKind, Stage, ExclusionReason])
def test_from_str_rejeita_valor_desconhecido(enum: type) -> None:
    with pytest.raises(PraxisForgeError):
        enum.from_str("inexistente")  # type: ignore[attr-defined]


def test_from_str_aceita_valor_conhecido() -> None:
    assert ArtifactKind.from_str("project_instruction") is ArtifactKind.PROJECT_INSTRUCTION
    assert Stage.from_str("discarded") is Stage.DISCARDED
    assert ExclusionReason.from_str("uncurated") is ExclusionReason.UNCURATED


@pytest.mark.parametrize(
    "campos",
    [
        {"path": ""},
        {"path": "/abs/x"},
        {"path": "a/../b"},
        {"path": ".."},
        {"path": "a/"},
        {"size": -1},
        {"files": 0},
        {"sha256": "abc"},
        {"sha256": "G" * 64},
    ],
)
def test_artefato_invalido(campos: dict[str, object]) -> None:
    with pytest.raises(InvalidCurationArtifactError):
        _artefato(**campos)


def test_exclusao_rejeita_path_absoluto() -> None:
    with pytest.raises(InvalidCurationArtifactError):
        ExcludedEntry(path="/etc", reason=ExclusionReason.FIXED_DIR, is_dir=True)


def test_manifesto_ordena_e_recusa_duplicado() -> None:
    manifesto = Manifest(
        alias="demo_a",
        conventions_version=SHA,
        artifacts=(_artefato(path="z.md"), _artefato(path="a.md")),
        excluded=(
            ExcludedEntry("y", ExclusionReason.BINARY, False),
            ExcludedEntry("b", ExclusionReason.BINARY, False),
        ),
    )
    assert [a.path for a in manifesto.artifacts] == ["a.md", "z.md"]
    assert [e.path for e in manifesto.excluded] == ["b", "y"]
    with pytest.raises(InvalidCurationArtifactError):
        Manifest("demo_a", SHA, (_artefato(path="a"), _artefato(path="a")), ())


@pytest.mark.parametrize(
    ("stage", "verdict", "esperado"),
    [
        (Stage.PROMOTED, None, True),
        (Stage.DISCARDED, None, True),
        (Stage.REMOVED, None, True),
        (Stage.REVIEWED, "accepted", True),
        (Stage.REVIEWED, None, False),
        (Stage.REVIEWED, "rejected", False),
        (Stage.PENDING, "accepted", False),
        (Stage.FAILED, None, False),
    ],
)
def test_is_final(stage: Stage, verdict: str | None, esperado: bool) -> None:
    assert is_final(stage, verdict) is esperado
