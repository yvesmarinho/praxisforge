# -*- coding: utf-8 -*-
"""
NOME: registry_location.py
TITULO: Local do registro de pastas fora do repositório (precedência) e registro antigo
DATA: 24/09/2026 14:31
MODIFICADO: 24/09/2026 14:31
VERSÃO: 0.1.0
DEPEND: pyyaml, praxisforge.infrastructure.yaml_loader
HISTÓRICO:
    - 24/09/2026 14:31: criação (T007, feature 007) — faz test_registry_location.py passar
STATUS: DEV
"""

from collections.abc import Mapping
from pathlib import Path

import yaml

from praxisforge.infrastructure.yaml_loader import NoTimestampSafeLoader

_ENV_REGISTRY = "PRAXISFORGE_REGISTRY"
_ENV_XDG = "XDG_CONFIG_HOME"
_SUBDIR = "praxisforge"
_FILENAME = "folders.yaml"
_LEGACY = Path("src") / "data" / "folders.yaml"


def _materializar(raw: Path, home: Path, cwd: Path) -> Path:
    """Expande `~` com o `home` recebido e resolve relativo contra `cwd`."""
    partes = raw.parts
    if partes and partes[0] == "~":
        raw = home.joinpath(*partes[1:])
    return raw if raw.is_absolute() else cwd / raw


def resolve_registry_path(
    cli_value: Path | None, env: Mapping[str, str], home: Path, cwd: Path
) -> Path:
    """
    Resolve o local do registro: `--registry` > `PRAXISFORGE_REGISTRY` > XDG > `~/.config`.

    :param cli_value: valor de `--registry` (None quando não informado).
    :type cli_value: Path | None
    :param env: variáveis de ambiente.
    :type env: Mapping[str, str]
    :param home: pasta pessoal do usuário.
    :type home: Path
    :param cwd: diretório atual (base de caminhos relativos).
    :type cwd: Path
    :return: caminho absoluto do registro.
    :rtype: Path

    :Example:

    >>> resolve_registry_path(None, {}, Path("/h"), Path("/w"))
    PosixPath('/h/.config/praxisforge/folders.yaml')
    >>> resolve_registry_path(None, {"XDG_CONFIG_HOME": "/x"}, Path("/h"), Path("/w"))
    PosixPath('/x/praxisforge/folders.yaml')
    """
    if cli_value is not None:
        return _materializar(cli_value, home, cwd)
    registro = env.get(_ENV_REGISTRY, "")
    if registro:
        return _materializar(Path(registro), home, cwd)
    xdg = env.get(_ENV_XDG, "")
    if xdg and Path(xdg).is_absolute():
        return Path(xdg) / _SUBDIR / _FILENAME
    return home / ".config" / _SUBDIR / _FILENAME


def find_legacy_registry(cwd: Path) -> Path | None:
    """
    Procura o registro antigo `src/data/folders.yaml` (a partir de `cwd`) com ao menos uma pasta.

    :param cwd: diretório atual.
    :type cwd: Path
    :return: caminho do registro antigo, ou None se ausente, vazio ou ilegível.
    :rtype: Path | None
    """
    arquivo = cwd / _LEGACY
    try:
        conteudo = arquivo.read_text(encoding="utf-8")
        # NoTimestampSafeLoader só remove o resolvedor de timestamp do SafeLoader
        documento = yaml.load(conteudo, Loader=NoTimestampSafeLoader)  # noqa: S506 # nosec B506
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(documento, dict):
        return None
    pastas = documento.get("folders")
    return arquivo if isinstance(pastas, dict) and pastas else None
