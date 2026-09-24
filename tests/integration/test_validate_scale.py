# -*- coding: utf-8 -*-
"""
NOME: test_validate_scale.py
TITULO: Teste de desempenho — 200 pastas listadas e validadas em < 5s (SC-003)
DATA: 22/09/2026 10:30
MODIFICADO: 23/09/2026 17:00
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 10:30: criação (T054)
    - 23/09/2026 17:00: registro v2 com path (feature 005)
STATUS: DEV
"""

import time
from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


@pytest.mark.slow
def test_200_pastas_listagem_e_validacao_em_menos_de_5s(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Listar e validar 200 pastas completa em menos de 5 segundos (SC-003)."""
    linhas = ["schema_version: '2'", "folders:"]
    for i in range(200):
        linhas.append(f"  pasta{i:04d}:")
        linhas.append("    description: pasta de teste")
        linhas.append("    content_type: docs")
        linhas.append("    license: MIT")
        linhas.append("    last_scanned: null")
        linhas.append("    status: not_scanned")
        linhas.append(f"    path: /srv/pastas/pasta{i:04d}")
    tmp_registry_path.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    inicio = time.monotonic()
    code_list = main(["--registry", str(tmp_registry_path), "folders", "list"])
    code_validate = main(["--registry", str(tmp_registry_path), "folders", "validate"])
    duracao = time.monotonic() - inicio

    assert code_list == 0
    assert code_validate == 0
    assert duracao < 5.0
