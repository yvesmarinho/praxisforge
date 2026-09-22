# -*- coding: utf-8 -*-
"""
NOME: test_layer_checker.py
TITULO: Testes de falha — layer_checker contra um pacote sintético
DATA: 22/09/2026 09:45
MODIFICADO: 22/09/2026 09:53
VERSÃO: 0.1.0
DEPEND: pytest, tests.architecture.layer_checker
HISTÓRICO:
    - 22/09/2026 09:45: criação (T061)
STATUS: DEV
"""

from pathlib import Path

from tests.architecture.layer_checker import check_layers


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _synthetic_package(tmp_path: Path) -> Path:
    root = tmp_path / "pkg"
    for layer in ("domain", "application", "infrastructure", "presentation"):
        _write(root, f"{layer}/__init__.py", "")
    return root


def test_domain_importando_lib_externa_eh_violacao(tmp_path: Path) -> None:
    """domain importando yaml/pydantic/requests é uma violação."""
    root = _synthetic_package(tmp_path)
    _write(root, "domain/x.py", "import yaml\n")
    violations = check_layers(root, "pkg")
    assert any(v.module == "pkg.domain.x" and v.imported == "yaml" for v in violations)


def test_domain_importando_logging_eh_violacao(tmp_path: Path) -> None:
    """domain importando logging é uma violação."""
    root = _synthetic_package(tmp_path)
    _write(root, "domain/x.py", "import logging\n")
    violations = check_layers(root, "pkg")
    assert any(v.module == "pkg.domain.x" and v.imported == "logging" for v in violations)


def test_domain_importando_infrastructure_eh_violacao(tmp_path: Path) -> None:
    """domain importando pkg.infrastructure é uma violação."""
    root = _synthetic_package(tmp_path)
    _write(root, "domain/x.py", "import pkg.infrastructure\n")
    violations = check_layers(root, "pkg")
    assert any(v.imported == "pkg.infrastructure" for v in violations)


def test_application_importando_infrastructure_eh_violacao(tmp_path: Path) -> None:
    """application importando infrastructure é uma violação."""
    root = _synthetic_package(tmp_path)
    _write(root, "application/x.py", "import pkg.infrastructure\n")
    violations = check_layers(root, "pkg")
    assert any(v.imported == "pkg.infrastructure" for v in violations)


def test_application_importando_presentation_eh_violacao(tmp_path: Path) -> None:
    """application importando presentation é uma violação."""
    root = _synthetic_package(tmp_path)
    _write(root, "application/x.py", "import pkg.presentation\n")
    violations = check_layers(root, "pkg")
    assert any(v.imported == "pkg.presentation" for v in violations)


def test_infrastructure_importando_presentation_eh_violacao(tmp_path: Path) -> None:
    """infrastructure importando presentation é uma violação."""
    root = _synthetic_package(tmp_path)
    _write(root, "infrastructure/x.py", "import pkg.presentation\n")
    violations = check_layers(root, "pkg")
    assert any(v.imported == "pkg.presentation" for v in violations)


def test_presentation_importando_domain_diretamente_eh_violacao(tmp_path: Path) -> None:
    """presentation importando domain diretamente é uma violação."""
    root = _synthetic_package(tmp_path)
    _write(root, "presentation/outro.py", "import pkg.domain\n")
    violations = check_layers(root, "pkg")
    assert any(v.imported == "pkg.domain" for v in violations)


def test_cli_importando_infrastructure_eh_permitido(tmp_path: Path) -> None:
    """presentation/cli.py (ponto de composição) pode importar infrastructure."""
    root = _synthetic_package(tmp_path)
    _write(root, "presentation/cli.py", "import pkg.infrastructure\n")
    violations = check_layers(root, "pkg")
    assert not any(v.module == "pkg.presentation.cli" for v in violations)


def test_mensagem_cita_modulo_import_e_regra(tmp_path: Path) -> None:
    """A violação cita módulo, import e regra."""
    root = _synthetic_package(tmp_path)
    _write(root, "domain/x.py", "import yaml\n")
    violations = check_layers(root, "pkg")
    violation = next(v for v in violations if v.imported == "yaml")
    assert violation.module == "pkg.domain.x"
    assert violation.imported == "yaml"
    assert violation.rule
