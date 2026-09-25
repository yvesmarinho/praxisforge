# -*- coding: utf-8 -*-
"""
NOME: skills_helpers.py
TITULO: Auxiliares de teste — projeto temporário com skills/, fontes e schemas (feature 008)
DATA: 24/09/2026 16:54
MODIFICADO: 25/09/2026 09:55
VERSÃO: 0.1.0
DEPEND: (stdlib)
HISTÓRICO:
    - 24/09/2026 16:54: criação (T012–T014, feature 008)
    - 25/09/2026 09:55: marcador pyproject.toml (raiz do projeto)
STATUS: DEV
"""

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def criar_projeto(root: Path) -> Path:
    """Cria projeto mínimo: marcador pyproject.toml, schemas/ reais, skills/ e fontes vazios."""
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    (root / "pyproject.toml").write_text('[project]\nname = "praxisforge"\n', encoding="utf-8")
    (root / "skills").mkdir(parents=True)
    (root / "src" / "data" / "sources").mkdir(parents=True)
    return root


def escrever_skill(
    root: Path,
    nome: str,
    *,
    version: str = "1.0.0",
    sources: list[str] | None = None,
    authored: bool | None = None,
    description: str = "Descrição da skill",
    corpo: str = "Instruções.\n",
    frontmatter_name: str | None = None,
    arquivos: dict[str, str] | None = None,
) -> Path:
    """Grava skills/<nome>/SKILL.md (e arquivos de apoio) com o frontmatter pedido."""
    pasta = root / "skills" / nome
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = [
        "---",
        f"name: {frontmatter_name or nome}",
        f"description: {description}",
        "metadata:",
        f"  version: '{version}'",
    ]
    if sources is not None:
        linhas.append("  sources: [" + ", ".join(sources) + "]")
    if authored is not None:
        linhas.append(f"  authored: {'true' if authored else 'false'}")
    linhas.append("---")
    (pasta / "SKILL.md").write_text("\n".join(linhas) + "\n" + corpo, encoding="utf-8")
    for relativo, conteudo in (arquivos or {}).items():
        destino = pasta / relativo
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
    return pasta


def escrever_fonte(root: Path, categoria: str, slug: str, policy: str = "summary") -> Path:
    """Grava src/data/sources/<categoria>/<slug>.md válido no source-schema-v2."""
    pasta = root / "src" / "data" / "sources" / categoria
    pasta.mkdir(parents=True, exist_ok=True)
    extra = "notice_preserved: true\n" if policy == "verbatim" else ""
    arquivo = pasta / f"{slug}.md"
    arquivo.write_text(
        "---\n"
        "schema_version: '2'\n"
        "origin: https://github.com/exemplo/repo\n"
        "author: Fulano\n"
        "date: '2026-09-20'\n"
        "license: MIT\n"
        "relevance: padrões\n"
        "status: active\n"
        f"extract_policy: {policy}\n"
        f"{extra}"
        "---\n"
        "Resumo.\n",
        encoding="utf-8",
    )
    return arquivo
