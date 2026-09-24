# -*- coding: utf-8 -*-
"""
NOME: filesystem_skill_repository.py
TITULO: Adapter de SkillRepository sobre o filesystem (skills/<nome>/SKILL.md)
DATA: 24/09/2026 16:54
MODIFICADO: 24/09/2026 16:54
VERSÃO: 0.1.0
DEPEND: pyyaml, praxisforge.domain, praxisforge.application.ports
HISTÓRICO:
    - 24/09/2026 16:54: criação (T017, feature 008)
STATUS: DEV
"""

import hashlib
from pathlib import Path

import yaml

from praxisforge.application.ports import SkillDocument, SkillRepository
from praxisforge.domain.errors import InvalidSkillError, SkillNotFoundError, Violation
from praxisforge.domain.skill import extract_references
from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader

_DELIMITER = "---"
_SKILL_FILE = "SKILL.md"
MARKER_FILE = ".praxisforge-skill.json"
_IGNORED_DIRS = ("__pycache__",)


def _invalida(name: str, reason: str) -> InvalidSkillError:
    return InvalidSkillError(name, [Violation(_SKILL_FILE, reason)])


def _split_frontmatter(name: str, conteudo: str) -> tuple[dict[str, object], str]:
    linhas = conteudo.split("\n")
    if linhas[0].strip() != _DELIMITER:
        raise _invalida(name, "sem frontmatter")
    try:
        fim = linhas[1:].index(_DELIMITER) + 1
    except ValueError as error:
        raise _invalida(name, "frontmatter não fechado") from error
    try:
        # NoTimestampSafeLoader só remove o resolvedor de timestamp do SafeLoader
        documento = yaml.load("\n".join(linhas[1:fim]), Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
    except yaml.YAMLError as error:
        raise _invalida(name, f"frontmatter corrompido: {error}") from error
    if not isinstance(documento, dict):
        raise _invalida(name, "frontmatter não é um mapa")
    return documento, "\n".join(linhas[fim + 1 :])


def _dentro(pasta: Path, relativo: str) -> Path | None:
    """Caminho do alvo quando fica dentro da pasta; None quando sai dela (a entidade acusa)."""
    if relativo.startswith(("/", "\\")) or ":" in relativo:
        return None
    alvo = (pasta / relativo).resolve()
    return alvo if alvo.is_relative_to(pasta.resolve()) else None


class FilesystemSkillRepository(SkillRepository):
    """
    Lê skills de `<skills_dir>/<nome>/SKILL.md`.

    :param skills_dir: pasta `skills/` do repositório.
    :type skills_dir: Path
    """

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = skills_dir

    def list_names(self) -> list[str]:
        """Ver SkillRepository.list_names."""
        if not self._skills_dir.is_dir():
            return []
        return sorted(
            item.name
            for item in self._skills_dir.iterdir()
            if item.is_dir() and not item.name.startswith(("_", "."))
        )

    def skill_dir(self, name: str) -> Path:
        """Ver SkillRepository.skill_dir."""
        return self._skills_dir / name

    def load(self, name: str) -> SkillDocument:
        """Ver SkillRepository.load."""
        pasta = self.skill_dir(name)
        if not pasta.is_dir():
            raise SkillNotFoundError(name)
        arquivo = pasta / _SKILL_FILE
        if not arquivo.exists():
            raise _invalida(name, "arquivo ausente")
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise _invalida(name, f"ilegível ({type(error).__name__})") from error
        frontmatter, corpo = _split_frontmatter(name, conteudo)
        referencias = extract_references(corpo)
        ausentes = []
        for referencia in referencias:
            alvo = _dentro(pasta, referencia)
            if alvo is not None and not alvo.exists():
                ausentes.append(referencia)
        return SkillDocument(
            folder_name=name,
            frontmatter=frontmatter,
            references=referencias,
            missing_references=ausentes,
        )

    def content_hash(self, name: str) -> str:
        """Ver SkillRepository.content_hash."""
        pasta = self.skill_dir(name)
        digest = hashlib.sha256()
        arquivos = sorted(
            item
            for item in pasta.rglob("*")
            if item.is_file()
            and item.name != MARKER_FILE
            and not any(parte in _IGNORED_DIRS for parte in item.relative_to(pasta).parts)
        )
        for item in arquivos:
            digest.update(item.relative_to(pasta).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(item.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()
