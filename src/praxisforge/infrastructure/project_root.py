# -*- coding: utf-8 -*-
"""
NOME: project_root.py
TITULO: Localiza a raiz do projeto praxisforge (schemas/, skills/, src/data/sources/)
DATA: 25/09/2026 09:56
MODIFICADO: 25/09/2026 09:56
VERSÃO: 0.1.0
DEPEND: (stdlib) tomllib, praxisforge.domain.errors
HISTÓRICO:
    - 25/09/2026 09:56: criação — CLI deixa de depender de rodar na raiz do repositório
STATUS: DEV
"""

import tomllib
from collections.abc import Mapping
from pathlib import Path

from praxisforge.domain.errors import ProjectRootNotFoundError

_ENV_ROOT = "PRAXISFORGE_ROOT"
_MARCADOR = "pyproject.toml"
_NOME_PROJETO = "praxisforge"


def find_project_root(cwd: Path, env: Mapping[str, str]) -> Path:
    """
    Devolve a raiz do projeto praxisforge.

    Precedência: `PRAXISFORGE_ROOT` (absoluto, obrigatoriamente uma raiz válida) >
    primeiro ancestral de `cwd` (inclusive) com `pyproject.toml` cujo `[project].name`
    é `praxisforge` — como o git acha o `.git`.

    :param cwd: diretório atual (ponto de partida da busca).
    :type cwd: Path
    :param env: variáveis de ambiente.
    :type env: Mapping[str, str]
    :return: diretório raiz do projeto.
    :rtype: Path
    :raises ProjectRootNotFoundError: variável inválida ou nenhum ancestral é a raiz.

    :Example:

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     raiz = Path(tmp)
    ...     _ = (raiz / "pyproject.toml").write_text('[project]\\nname = "praxisforge"\\n')
    ...     (raiz / "skills").mkdir()
    ...     find_project_root(raiz / "skills", {}) == raiz
    True
    """
    valor = env.get(_ENV_ROOT, "")
    if valor:
        declarada = Path(valor)
        if not declarada.is_absolute():
            raise ProjectRootNotFoundError(f"{_ENV_ROOT} deve ser um caminho absoluto: {valor}")
        if not _eh_raiz(declarada):
            raise ProjectRootNotFoundError(
                f"{_ENV_ROOT} não aponta para a raiz do praxisforge: {valor}"
            )
        return declarada
    for pasta in (cwd, *cwd.parents):
        if _eh_raiz(pasta):
            return pasta
    raise ProjectRootNotFoundError(
        f"nenhum {_MARCADOR} do praxisforge em {cwd} ou acima — "
        f"rode dentro do repositório ou defina {_ENV_ROOT}"
    )


def _eh_raiz(pasta: Path) -> bool:
    """True se `pasta/pyproject.toml` é legível e declara o projeto praxisforge."""
    try:
        dados = tomllib.loads((pasta / _MARCADOR).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    projeto = dados.get("project")
    return isinstance(projeto, dict) and projeto.get("name") == _NOME_PROJETO
