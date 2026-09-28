# -*- coding: utf-8 -*-
"""
NOME: test_triage_incremental.py
TITULO: Testes de falha — triagem incremental quando o fork muda (US5, feature 011)
DATA: 28/09/2026 16:23
MODIFICADO: 28/09/2026 16:23
VERSÃO: 0.1.0
DEPEND: pytest, tests.triage_helpers
HISTÓRICO:
    - 28/09/2026 16:23: criação (T049, feature 011)
STATUS: DEV
"""

from pathlib import Path

from praxisforge.application.ports import ModelRole
from tests.triage_helpers import TriageEnv, triagem

DEZ = {f"rules/r{n}.md": f"regra {n}" for n in range(10)}


def test_so_o_alterado_volta_para_a_triagem(tmp_path: Path) -> None:
    env = TriageEnv(tmp_path)
    env.registrar("demo_a", DEZ)
    env.triar("demo_a")
    assert env.model.calls() == 10
    env.escrever("demo_a", {"rules/r3.md": "regra 3 alterada"})
    env.inventariar("demo_a")
    env.model.requests.clear()
    env.triar("demo_a")
    assert env.model.calls(ModelRole.TRIAGE) == 1  # SC-003
    assert "rules/r3.md" in env.model.requests[0].user_prompt


def test_rascunho_do_alterado_e_substituido(tmp_path: Path) -> None:
    env = TriageEnv(tmp_path)
    env.registrar("demo_a", {"rules/a.md": "versão 1"})
    env.model.default(ModelRole.TRIAGE, triagem("gap"))
    env.triar("demo_a")
    primeiro = env.drafts.list_pending()
    assert len(primeiro) == 1
    env.escrever("demo_a", {"rules/a.md": "versão 2"})
    env.inventariar("demo_a")
    env.model.default(
        ModelRole.DRAFT,
        {"kind": "rule", "name": "versao-nova", "description": "Nova.", "body": "# Nova\n"},
    )
    env.triar("demo_a")
    depois = env.drafts.list_pending()
    assert [d.draft_id for d in depois] == [primeiro[0].draft_id]  # sem órfão
    assert depois[0].proposal.name == "versao-nova"
    novo_hash = env.estado("demo_a")["rules/a.md"]["sha256"]
    assert [(o.path, o.sha256) for o in depois[0].origins] == [("rules/a.md", novo_hash)]
