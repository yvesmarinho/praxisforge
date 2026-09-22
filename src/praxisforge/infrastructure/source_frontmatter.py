# -*- coding: utf-8 -*-
"""
NOME: source_frontmatter.py
TITULO: Leitor de frontmatter YAML de arquivos de fonte (.md)
DATA: 22/09/2026 10:30
MODIFICADO: 22/09/2026 10:15
VERSÃO: 0.1.0
DEPEND: pyyaml, praxisforge.domain.errors
HISTÓRICO:
    - 22/09/2026 10:30: criação (T057) — faz tests/integration/test_source_frontmatter.py passar
STATUS: DEV
"""

from pathlib import Path

import yaml

from praxisforge.domain.errors import RegistryUnavailableError
from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader

_DELIMITER = "---"


def read_frontmatter(path: Path) -> dict[str, object]:
    """
    Lê o frontmatter YAML de um arquivo `.md` (entre `---`), sem executar código.

    :param path: caminho do arquivo `.md`.
    :type path: Path
    :return: documento do frontmatter (datas permanecem `str` ISO 8601).
    :rtype: dict[str, object]
    :raises RegistryUnavailableError: arquivo ilegível, sem frontmatter ou corrompido.
    """
    try:
        conteudo = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RegistryUnavailableError(f"fonte ilegível: {error}") from error
    linhas = conteudo.split("\n")
    if not linhas or linhas[0].strip() != _DELIMITER:
        raise RegistryUnavailableError("fonte sem frontmatter")
    try:
        fim = linhas[1:].index(_DELIMITER) + 1
    except ValueError as error:
        raise RegistryUnavailableError("fonte com frontmatter não fechado") from error
    bloco = "\n".join(linhas[1:fim])
    try:
        # NoTimestampSafeLoader só remove o resolvedor de timestamp do SafeLoader;
        # não adiciona construtores !!python/object (research.md D16)
        documento = yaml.load(bloco, Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
    except yaml.YAMLError as error:
        raise RegistryUnavailableError(f"frontmatter corrompido: {error}") from error
    if not isinstance(documento, dict):
        raise RegistryUnavailableError("frontmatter corrompido: não é um mapa")
    return documento
