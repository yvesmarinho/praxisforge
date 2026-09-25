# -*- coding: utf-8 -*-
"""
NOME: library_helpers.py
TITULO: Auxiliares de teste — projeto temporário com library/, fontes e schemas (feature 009)
DATA: 25/09/2026 13:02
MODIFICADO: 25/09/2026 13:02
VERSÃO: 0.1.0
DEPEND: (stdlib), pyyaml
HISTÓRICO:
    - 25/09/2026 13:02: criação (T015, feature 009) — sucede skills_helpers.py
STATUS: DEV
"""

import shutil
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
TIPOS = ("skills", "commands", "agents", "hooks", "rules", "references")
_COM_NOME = ("skill", "agent", "hook", "reference")


def criar_projeto(root: Path) -> Path:
    """Projeto mínimo: marcador pyproject.toml, schemas/ reais, library/<tipo>/ e fontes vazios."""
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    (root / "pyproject.toml").write_text('[project]\nname = "praxisforge"\n', encoding="utf-8")
    for tipo in TIPOS:
        (root / "library" / tipo).mkdir(parents=True)
    (root / "src" / "data" / "sources").mkdir(parents=True)
    return root


def escrever_item(
    root: Path,
    kind: str,
    nome: str,
    *,
    version: str = "1.0.0",
    sources: list[str] | None = None,
    authored: bool | None = True,
    description: str = "Descrição do item",
    corpo: str = "Instruções.\n",
    campos: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    arquivos: dict[str, str] | None = None,
) -> Path:
    """
    Grava um item em library/<kind>s/ com frontmatter válido por padrão.

    Tipos de pasta (skill, hook) viram <nome>/SKILL.md|HOOK.md; os demais <nome>.md.
    Hook recebe event=SessionStart e run=[run.sh] (com o script) quando não informados.
    """
    fm: dict[str, object] = {}
    if kind in _COM_NOME:
        fm["name"] = nome
    fm["description"] = description
    if kind == "hook":
        fm.setdefault("event", "SessionStart")
        fm.setdefault("run", ["run.sh"])
    fm.update(campos or {})
    meta: dict[str, object] = {"version": version}
    if sources is not None:
        meta["sources"] = sources
    if authored is not None:
        meta["authored"] = authored
    meta.update(metadata or {})
    fm["metadata"] = meta
    texto = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False) + "---\n" + corpo
    base = root / "library" / f"{kind}s"
    if kind in ("skill", "hook"):
        pasta = base / nome
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / ("SKILL.md" if kind == "skill" else "HOOK.md")).write_text(texto, encoding="utf-8")
        extras = dict(arquivos or {})
        if kind == "hook" and campos is None:
            extras.setdefault("run.sh", "#!/usr/bin/env bash\necho ok\n")
        for relativo, conteudo in extras.items():
            destino = pasta / relativo
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(conteudo, encoding="utf-8")
        return pasta
    base.mkdir(parents=True, exist_ok=True)
    arquivo = base / f"{nome}.md"
    arquivo.write_text(texto, encoding="utf-8")
    return arquivo


def escrever_fonte(root: Path, categoria: str, slug: str, versao: str = "3") -> Path:
    """Grava src/data/sources/<categoria>/<slug>.md válido no source-schema-v3 (ou v2)."""
    pasta = root / "src" / "data" / "sources" / categoria
    pasta.mkdir(parents=True, exist_ok=True)
    extra = "extract_policy: summary\n" if versao == "2" else ""
    arquivo = pasta / f"{slug}.md"
    arquivo.write_text(
        "---\n"
        f"schema_version: '{versao}'\n"
        "origin: https://github.com/exemplo/repo\n"
        "author: Fulano\n"
        "date: '2026-09-20'\n"
        "license: MIT\n"
        "relevance: padrões\n"
        "status: active\n"
        f"{extra}"
        "---\n"
        "Síntese.\n",
        encoding="utf-8",
    )
    return arquivo
