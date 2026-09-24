# -*- coding: utf-8 -*-
"""
NOME: test_publish_skills_script.py
TITULO: Testes de integração — scripts/publish-skills repassa para `skills publish` (FR-016)
DATA: 24/09/2026 16:48
MODIFICADO: 24/09/2026 16:50
VERSÃO: 0.1.0
DEPEND: pytest (subprocess, uv no PATH)
HISTÓRICO:
    - 24/09/2026 16:48: criação (T031, feature 008)
STATUS: DEV
"""

import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

import pytest

from tests.skills_helpers import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "publish-skills"
# HOME real capturado na importação (antes da fixture autouse), para o uv achar cache e Python
_HOME_REAL = Path(os.environ.get("HOME", str(Path.home())))


def _env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.setdefault("UV_CACHE_DIR", str(_HOME_REAL / ".cache" / "uv"))
    env.setdefault("UV_PYTHON_INSTALL_DIR", str(_HOME_REAL / ".local" / "share" / "uv" / "python"))
    return env


def test_script_executavel_com_shebang() -> None:
    """O atalho existe, é executável e começa com shebang."""
    assert os.access(SCRIPT, os.X_OK)
    assert SCRIPT.read_text(encoding="utf-8").startswith("#!")


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv indisponível")
@pytest.mark.parametrize(
    ("args", "codigo"),
    [(["--all", "--target", "global"], 0), (["--all", "--target", "global", "--nada"], 2)],
)
def test_script_repassa_argumentos_e_codigo(tmp_path: Path, args: list[str], codigo: int) -> None:
    """Saída e código iguais aos do comando, rodando de outro diretório."""
    home = tmp_path / "home"
    home.mkdir()
    uv = shutil.which("uv") or "uv"
    direto = subprocess.run(  # noqa: S603 # nosec B603
        [uv, "run", "praxisforge", "skills", "publish", *args],
        cwd=REPO_ROOT,
        env=_env(home),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    atalho = subprocess.run(  # noqa: S603 # nosec B603
        [str(SCRIPT), *args],
        cwd=tmp_path,
        env=_env(home),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert atalho.returncode == direto.returncode == codigo
    assert atalho.stdout == direto.stdout
