# -*- coding: utf-8 -*-
"""
NOME: test_publish_library_script.py
TITULO: Testes de integração — atalho scripts/publish-library
DATA: 25/09/2026 13:19
MODIFICADO: 25/09/2026 13:19
VERSÃO: 0.1.0
DEPEND: pytest
HISTÓRICO:
    - 25/09/2026 13:19: criação (T035, feature 009) — sucede test_publish_skills_script.py
STATUS: DEV
"""

import os
import shutil
import subprocess  # nosec B404
from pathlib import Path

import pytest

from tests.library_helpers import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "publish-library"
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
    ("extra", "codigo"),
    [(["--all", "--target", "APP"], 0), (["--all", "--target", "APP", "--nada"], 2)],
)
def test_script_repassa_argumentos_e_codigo(tmp_path: Path, extra: list[str], codigo: int) -> None:
    """Saída e código iguais aos do comando, rodando de outro diretório."""
    uv = shutil.which("uv") or "uv"
    saidas = []
    for rotulo, comando, cwd in (
        ("direto", [uv, "run", "praxisforge", "library", "publish"], REPO_ROOT),
        ("atalho", [str(SCRIPT)], tmp_path),
    ):
        app = tmp_path / f"app-{rotulo}"
        app.mkdir()
        home = tmp_path / f"home-{rotulo}"
        home.mkdir()
        args = [str(app) if a == "APP" else a for a in extra]
        saidas.append(
            subprocess.run(  # noqa: S603 # nosec B603
                [*comando, *args],
                cwd=cwd,
                env=_env(home),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        )
    direto, atalho = saidas
    assert atalho.returncode == direto.returncode == codigo
    assert atalho.stdout == direto.stdout
