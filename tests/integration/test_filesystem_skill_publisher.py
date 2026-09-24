# -*- coding: utf-8 -*-
"""
NOME: test_filesystem_skill_publisher.py
TITULO: Testes de integração — FilesystemSkillPublisher (cópia atômica, symlink, marcador)
DATA: 24/09/2026 16:48
MODIFICADO: 24/09/2026 16:49
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.infrastructure.filesystem_skill_publisher
HISTÓRICO:
    - 24/09/2026 16:48: criação (T028, feature 008)
STATUS: DEV
"""

import json
import os
import shutil
from pathlib import Path

import pytest

from praxisforge.domain.errors import ForeignSkillDestinationError, SkillPublicationError
from praxisforge.infrastructure.filesystem_skill_publisher import (
    MARKER_FILE,
    FilesystemSkillPublisher,
)
from praxisforge.infrastructure.jsonschema_validator import JsonSchemaContractValidator
from tests.skills_helpers import REPO_ROOT, escrever_skill

HASH = "a" * 64


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    escrever_skill(tmp_path, "alfa", authored=True, arquivos={"ref/a.md": "a"})
    return tmp_path / "skills"


@pytest.fixture
def destino(tmp_path: Path) -> Path:
    return tmp_path / "home" / ".claude" / "skills"


@pytest.fixture
def publisher(skills_dir: Path) -> FilesystemSkillPublisher:
    return FilesystemSkillPublisher(
        skills_dir, JsonSchemaContractValidator(schemas_dir=REPO_ROOT / "schemas")
    )


def _sem_temporarios(destino: Path) -> bool:
    return not [p for p in destino.iterdir() if p.name.startswith(".")]


def test_inspect_ausente(publisher: FilesystemSkillPublisher, destino: Path) -> None:
    """Destino inexistente → absent."""
    assert publisher.inspect(destino, "alfa").kind == "absent"


def test_publish_copy_grava_arquivos_e_marcador(
    publisher: FilesystemSkillPublisher, destino: Path
) -> None:
    """Cópia com arquivos de apoio e marcador válido; inspect reconhece como nossa."""
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    alvo = destino / "alfa"
    assert (alvo / "SKILL.md").is_file() and (alvo / "ref" / "a.md").is_file()
    marcador = json.loads((alvo / MARKER_FILE).read_text(encoding="utf-8"))
    assert marcador == {
        "schema_version": "1",
        "name": "alfa",
        "version": "1.0.0",
        "content_sha256": HASH,
        "source": "skills/alfa",
    }
    estado = publisher.inspect(destino, "alfa")
    assert (estado.kind, estado.version, estado.content_sha256) == ("copy", "1.0.0", HASH)
    assert _sem_temporarios(destino)


def test_publish_copy_substitui_destino_nosso(
    publisher: FilesystemSkillPublisher, destino: Path, skills_dir: Path
) -> None:
    """Nova cópia substitui a anterior (arquivo removido na origem some do destino)."""
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    (skills_dir / "alfa" / "ref" / "a.md").unlink()
    publisher.publish_copy(destino, "alfa", "1.1.0", "b" * 64)
    assert not (destino / "alfa" / "ref" / "a.md").exists()
    assert publisher.inspect(destino, "alfa").version == "1.1.0"
    assert _sem_temporarios(destino)


def test_publish_copy_falha_mantem_destino_antigo(
    publisher: FilesystemSkillPublisher, destino: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falha durante a cópia: destino antigo intacto e sem temporários (FR-015)."""
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)

    def _falhar(*_args: object, **_kwargs: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(shutil, "copytree", _falhar)
    with pytest.raises(SkillPublicationError):
        publisher.publish_copy(destino, "alfa", "2.0.0", "b" * 64)
    assert publisher.inspect(destino, "alfa").version == "1.0.0"
    assert _sem_temporarios(destino)


def test_publish_copy_sem_permissao(publisher: FilesystemSkillPublisher, destino: Path) -> None:
    """Destino sem permissão de escrita → SkillPublicationError."""
    destino.mkdir(parents=True)
    destino.chmod(0o500)
    try:
        with pytest.raises(SkillPublicationError):
            publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    finally:
        destino.chmod(0o700)


def test_publish_symlink_cria_e_troca(
    publisher: FilesystemSkillPublisher, destino: Path, skills_dir: Path
) -> None:
    """Symlink aponta para a pasta da skill; troca uma cópia nossa por link e vice-versa."""
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    publisher.publish_symlink(destino, "alfa")
    alvo = destino / "alfa"
    assert alvo.is_symlink() and alvo.resolve() == (skills_dir / "alfa").resolve()
    assert publisher.inspect(destino, "alfa").kind == "symlink"
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    assert not alvo.is_symlink() and publisher.inspect(destino, "alfa").kind == "copy"
    assert _sem_temporarios(destino)


def test_publish_symlink_sem_permissao(publisher: FilesystemSkillPublisher, destino: Path) -> None:
    """Falha ao criar o link → SkillPublicationError."""
    destino.mkdir(parents=True)
    destino.chmod(0o500)
    try:
        with pytest.raises(SkillPublicationError):
            publisher.publish_symlink(destino, "alfa")
    finally:
        destino.chmod(0o700)


@pytest.mark.parametrize(
    "caso", ["pasta", "marcador_invalido", "marcador_ilegivel", "link_alheio", "arquivo"]
)
def test_inspect_terceiro(
    publisher: FilesystemSkillPublisher, destino: Path, tmp_path: Path, caso: str
) -> None:
    """Pasta sem marcador, marcador inválido, link para outro lugar ou arquivo = terceiro."""
    destino.mkdir(parents=True)
    alvo = destino / "alfa"
    if caso == "pasta":
        alvo.mkdir()
    elif caso == "marcador_invalido":
        alvo.mkdir()
        (alvo / MARKER_FILE).write_text('{"schema_version": "1"}', encoding="utf-8")
    elif caso == "marcador_ilegivel":
        alvo.mkdir()
        (alvo / MARKER_FILE).write_text("{", encoding="utf-8")
    elif caso == "link_alheio":
        (tmp_path / "outro").mkdir()
        os.symlink(tmp_path / "outro", alvo)
    else:
        alvo.write_text("x", encoding="utf-8")
    assert publisher.inspect(destino, "alfa").kind == "foreign"


def test_remove_so_destinos_nossos(publisher: FilesystemSkillPublisher, destino: Path) -> None:
    """remove apaga cópia/link nossos e recusa terceiros."""
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    publisher.remove(destino, "alfa")
    assert not (destino / "alfa").exists()
    publisher.publish_symlink(destino, "alfa")
    publisher.remove(destino, "alfa")
    assert not (destino / "alfa").is_symlink()
    (destino / "alheia").mkdir()
    with pytest.raises(ForeignSkillDestinationError):
        publisher.remove(destino, "alheia")
    assert (destino / "alheia").is_dir()


def test_remove_sem_permissao(publisher: FilesystemSkillPublisher, destino: Path) -> None:
    """Falha de I/O na remoção → SkillPublicationError."""
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    destino.chmod(0o500)
    try:
        with pytest.raises(SkillPublicationError):
            publisher.remove(destino, "alfa")
    finally:
        destino.chmod(0o700)


def test_list_published_so_os_nossos(
    publisher: FilesystemSkillPublisher, destino: Path, skills_dir: Path
) -> None:
    """Lista cópias e links nossos (inclusive link órfão), nunca terceiros."""
    assert publisher.list_published(destino) == []
    publisher.publish_copy(destino, "alfa", "1.0.0", HASH)
    os.symlink(skills_dir / "sumida", destino / "sumida")
    (destino / "alheia").mkdir()
    (destino / ".oculta").mkdir()
    assert publisher.list_published(destino) == ["alfa", "sumida"]
