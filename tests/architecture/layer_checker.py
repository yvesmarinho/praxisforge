# -*- coding: utf-8 -*-
"""
NOME: layer_checker.py
TITULO: Verificador de regras de dependência entre camadas (AST, sem dependência nova)
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:53
VERSÃO: 0.1.0
DEPEND: (stdlib ast apenas)
HISTÓRICO:
    - 22/09/2026 09:45: criação (T064) — faz T061 e T062 passarem
STATUS: DEV
"""

import ast
from dataclasses import dataclass
from pathlib import Path

# Matriz de dependências permitidas (research.md D10).
# "presentation/cli.py" é o único módulo de presentation que pode importar infrastructure
# (ponto de composição).
_ALLOWED_EXTERNAL_BY_LAYER: dict[str, set[str]] = {
    "domain": set(),  # só stdlib e praxisforge.domain
    "application": set(),  # só stdlib, praxisforge.domain e praxisforge.application
    "infrastructure": set(),  # stdlib + libs externas + domain + application
    "presentation": set(),  # stdlib + praxisforge.application (+ infra só em cli.py)
}

_LAYER_ALLOWED_INTERNAL: dict[str, set[str]] = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "infrastructure": {"domain", "application", "infrastructure"},
    "presentation": {"application", "presentation"},
}


@dataclass(frozen=True)
class LayerViolation:
    """
    Uma violação de regra de dependência entre camadas.

    :param module: módulo (dot-path relativo ao pacote raiz) onde a violação ocorreu.
    :type module: str
    :param imported: nome do módulo importado que viola a regra.
    :type imported: str
    :param rule: descrição da regra violada.
    :type rule: str
    """

    module: str
    imported: str
    rule: str


def _module_dotpath(file: Path, package_root: Path) -> str:
    relative = file.relative_to(package_root.parent)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _layer_of(dotpath: str, root_package: str) -> str | None:
    prefix = f"{root_package}."
    if not dotpath.startswith(prefix):
        return None
    rest = dotpath[len(prefix) :]
    layer = rest.split(".", 1)[0]
    return layer if layer in _LAYER_ALLOWED_INTERNAL else None


def _imported_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return [node.module]
    return []


def check_layers(package_root: Path, root_package: str) -> list[LayerViolation]:
    """
    Percorre os módulos `.py` sob `package_root` e aplica a matriz de dependências.

    :param package_root: diretório do pacote raiz (ex.: `src/praxisforge`).
    :type package_root: Path
    :param root_package: nome do pacote raiz (ex.: `"praxisforge"`).
    :type root_package: str
    :return: lista de violações encontradas (vazia se conforme).
    :rtype: list[LayerViolation]
    """
    violations: list[LayerViolation] = []
    for file in sorted(package_root.rglob("*.py")):
        module_dotpath = _module_dotpath(file, package_root)
        layer = _layer_of(module_dotpath, root_package)
        if layer is None:
            continue
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        is_composition_point = layer == "presentation" and file.name == "cli.py"
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for imported in _imported_names(node):
                if imported == "logging" or imported.startswith("logging."):
                    if layer == "domain":
                        violations.append(
                            LayerViolation(
                                module=module_dotpath,
                                imported=imported,
                                rule="domain não usa logging",
                            )
                        )
                    continue
                imported_layer = _layer_of(imported, root_package)
                if imported_layer is not None:
                    if imported_layer == "infrastructure" and is_composition_point:
                        continue
                    if imported_layer not in _LAYER_ALLOWED_INTERNAL[layer]:
                        violations.append(
                            LayerViolation(
                                module=module_dotpath,
                                imported=imported,
                                rule=f"{layer} não pode importar {imported_layer}",
                            )
                        )
                elif imported.split(".", 1)[0] not in _stdlib_allowed(layer):
                    if layer == "domain":
                        violations.append(
                            LayerViolation(
                                module=module_dotpath,
                                imported=imported,
                                rule="domain só pode importar stdlib e praxisforge.domain",
                            )
                        )
    return violations


_STDLIB_TOP_LEVEL_BLOCKLIST_FOR_DOMAIN = {"yaml", "pydantic", "requests", "jsonschema", "logging"}


def _stdlib_allowed(layer: str) -> set[str]:
    """Para 'domain', bloqueia libs externas conhecidas; para as demais, tudo é permitido."""
    if layer == "domain":
        import sys

        return set(sys.stdlib_module_names) - _STDLIB_TOP_LEVEL_BLOCKLIST_FOR_DOMAIN
    return {"*"}  # sentinel: não usado para outras camadas (checagem só por internal layer)
