# -*- coding: utf-8 -*-
"""
NOME: test_cli_validate.py
TITULO: Testes de falha — CLI praxisforge folders validate / sources validate
DATA: 22/09/2026 10:30
MODIFICADO: 24/09/2026 10:54
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.presentation.cli
HISTÓRICO:
    - 22/09/2026 10:30: criação (T053)
    - 23/09/2026 16:54: registro v2 com path (T022, feature 005)
    - 24/09/2026 10:54: sources validate com source-schema-v2 e política de extração
      (T014, feature 006)
STATUS: DEV
"""

from pathlib import Path

import pytest

from praxisforge.presentation.cli import main


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_folders_validate_registro_valido_codigo_0(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders validate com registro válido retorna código 0."""
    tmp_registry_path.write_text(
        "schema_version: '2'\n"
        "folders:\n"
        "  github_forks:\n"
        "    description: d\n"
        "    content_type: docs\n"
        "    license: unknown\n"
        "    last_scanned: null\n"
        "    status: pending\n"
        "    path: /srv/pastas/github_forks\n",
        encoding="utf-8",
    )
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "validate"], capsys)
    assert code == 0
    assert "1 ok" in out


def test_folders_validate_lista_violacoes_e_resumo_codigo_1(
    tmp_registry_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """folders validate com pasta inválida lista violações e retorna código 1."""
    tmp_registry_path.write_text(
        "schema_version: '2'\n"
        "folders:\n"
        "  invalida:\n"
        "    description: d\n"
        "    content_type: docs\n"
        "    license: unknown\n"
        "    last_scanned: null\n"
        "    status: scanned\n"  # unknown exige pending
        "    path: /srv/pastas/invalida\n",
        encoding="utf-8",
    )
    code, out, _ = _run(["--registry", str(tmp_registry_path), "folders", "validate"], capsys)
    assert code == 1
    assert "com falha" in out


_FONTE = (
    "---\nschema_version: '2'\norigin: https://x\nauthor: Fulano\ndate: 2026-09-21\n"
    "license: {licenca}\nrelevance: y\nstatus: active\nextract_policy: {politica}\n"
    "notice_preserved: true\n{extra}---\ncorpo\n"
)


def _fonte(
    pasta: Path, nome: str, licenca: str = "MIT", politica: str = "verbatim", extra: str = ""
) -> Path:
    arquivo = pasta / nome
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(
        _FONTE.format(licenca=licenca, politica=politica, extra=extra), encoding="utf-8"
    )
    return arquivo


def test_sources_validate_arquivo_e_diretorio(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """sources validate aceita arquivo ou diretório; falha por item não interrompe o lote."""
    valido = _fonte(tmp_path, "valido.md")
    (tmp_path / "invalido.md").write_text("sem frontmatter\n", encoding="utf-8")

    code, out, _ = _run(["sources", "validate", str(valido)], capsys)
    assert code == 0
    assert "1 ok, 0 com falha" in out

    code, out, _ = _run(["sources", "validate", str(tmp_path)], capsys)
    assert code == 1
    assert "1 ok" in out
    assert "1 com falha" in out


def test_sources_validate_varre_subpastas_de_categoria(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """src/data/sources/<categoria>/<slug>.md: diretório é varrido recursivamente."""
    _fonte(tmp_path, "agentes/a.md")
    _fonte(tmp_path, "prompts/b.md")
    code, out, _ = _run(["sources", "validate", str(tmp_path)], capsys)
    assert code == 0
    assert "2 ok, 0 com falha" in out


def test_sources_validate_politica_acima_da_maxima_codigo_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Elastic-2.0 verbatim → mensagem com licença, declarada, máxima e escopo (SC-003)."""
    arquivo = _fonte(tmp_path, "elastic.md", licenca="Elastic-2.0")
    code, out, _ = _run(["sources", "validate", str(arquivo)], capsys)
    assert code == 1
    assert (
        "política 'verbatim' excede a máxima 'summary' para a licença Elastic-2.0 (escopo: code)"
        in out
    )
    assert "0 ok, 1 com falha" in out


def test_sources_validate_registro_v1_pede_extract_policy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Frontmatter v1 → falha pedindo extract_policy (FR-014)."""
    arquivo = tmp_path / "v1.md"
    arquivo.write_text(
        "---\nschema_version: '1'\norigin: https://x\ndate: 2026-09-21\nlicense: MIT\n"
        "relevance: y\nstatus: active\nextract_allowed: true\n---\n",
        encoding="utf-8",
    )
    code, out, _ = _run(["sources", "validate", str(arquivo)], capsys)
    assert code == 1
    assert "extract_policy" in out


def test_sources_validate_diretorio_vazio_codigo_0(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nada a validar: 0 ok, 0 com falha."""
    code, out, _ = _run(["sources", "validate", str(tmp_path)], capsys)
    assert code == 0
    assert "0 ok, 0 com falha" in out


@pytest.mark.parametrize(
    ("extra", "codigo", "trecho"),
    [
        ("", 1, "(escopo: code)"),
        ("extract_scope: code\n", 1, "(escopo: code)"),
        ("extract_scope: docs\n", 0, "1 ok, 0 com falha"),
    ],
)
def test_sources_validate_gpl_por_escopo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], extra: str, codigo: int, trecho: str
) -> None:
    """GPL-3.0 verbatim: só documentação passa (FR-010)."""
    arquivo = _fonte(tmp_path, "gpl.md", licenca="GPL-3.0", extra=extra)
    code, out, _ = _run(["sources", "validate", str(arquivo)], capsys)
    assert code == codigo
    assert trecho in out
