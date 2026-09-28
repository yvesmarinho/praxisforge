# -*- coding: utf-8 -*-
"""
NOME: test_triage_folders.py
TITULO: Testes de falha — caso de uso da triagem com modelo falso (feature 011)
DATA: 28/09/2026 16:00
MODIFICADO: 28/09/2026 16:00
VERSÃO: 0.1.0
DEPEND: pytest, praxisforge.application.triage_folders, tests.triage_helpers
HISTÓRICO:
    - 28/09/2026 16:00: criação — US1 (T024, feature 011)
    - 28/09/2026 16:18: US2 — rascunhos, similaridade e fusões (T036)
STATUS: DEV
"""

import json
import logging
from decimal import Decimal
from pathlib import Path

import pytest

from praxisforge.application.ports import ModelRole
from praxisforge.domain.errors import (
    CurationLockedError,
    CurationNotInventoriedError,
    DraftStoreCorruptError,
    FolderNotFoundError,
    LanguageModelResponseInvalidError,
    LanguageModelUnavailableError,
    LanguageModelUntestedVersionError,
    PromptSetError,
)
from tests.library_helpers import escrever_item
from tests.triage_helpers import TriageEnv, triagem

TRES = {"a.md": "# A\nconteúdo A", "b.md": "# B\nconteúdo B", "c.md": "# C\nconteúdo C"}


@pytest.fixture
def env(tmp_path: Path) -> TriageEnv:
    return TriageEnv(tmp_path)


# --- US1: vereditos -------------------------------------------------------------------


def test_tres_pendentes_viram_tres_vereditos(env: TriageEnv) -> None:
    escrever_item(env.project, "skill", "testes-primeiro", description="tdd testes")
    env.registrar("demo_a", TRES)
    env.model.script(
        ModelRole.TRIAGE, "a.md", triagem("covered", covered_by=["skill/testes-primeiro"])
    )
    env.model.script(ModelRole.TRIAGE, "b.md", triagem("out_of_scope"))
    env.model.script(ModelRole.TRIAGE, "c.md", triagem("out_of_scope"))
    relatorio = env.triar("demo_a")
    pasta = relatorio.folders[0]
    assert pasta.verdicts == {"covered": 1, "gap": 0, "out_of_scope": 2}
    assert pasta.failures == [] and pasta.remaining == 0
    estado = env.estado("demo_a")
    assert {p: s["stage"] for p, s in estado.items()} == dict.fromkeys(TRES, "triaged")
    assert estado["a.md"]["triage"]["covered_by"] == ["skill/testes-primeiro"]
    assert estado["a.md"]["triage"]["model"] == "fake-haiku"
    assert relatorio.calls == 3 and relatorio.stop_reason == "done"


def test_ordem_por_caminho(env: TriageEnv) -> None:
    env.registrar("demo_a", {"z.md": "z", "a.md": "a", "m.md": "m"})
    env.triar("demo_a")
    caminhos = [r.user_prompt.split("Artefato: ")[1].split(" ")[0] for r in env.model.requests]
    assert caminhos == ["a.md", "m.md", "z.md"]


def test_estado_gravado_a_cada_artefato(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.model.script(ModelRole.TRIAGE, "c.md", KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        env.triar("demo_a")
    etapas = {p: s["stage"] for p, s in env.estado("demo_a").items()}
    assert etapas == {"a.md": "triaged", "b.md": "triaged", "c.md": "pending"}


def test_item_citado_inexistente_vira_falha(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.model.script(ModelRole.TRIAGE, "a.md", triagem("covered", covered_by=["skill/fantasma"]))
    pasta = env.triar("demo_a").folders[0]
    assert [(f.path, f.error_type) for f in pasta.failures] == [("a.md", "InvalidTriageError")]
    estado = env.estado("demo_a")["a.md"]
    assert (estado["stage"], estado["attempts"], estado["last_error"]) == (
        "failed",
        1,
        "InvalidTriageError",
    )
    assert env.estado("demo_a")["b.md"]["stage"] == "triaged"


def test_resposta_invalida_nao_derruba_o_lote(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.model.script(ModelRole.TRIAGE, "b.md", LanguageModelResponseInvalidError("x"))
    pasta = env.triar("demo_a").folders[0]
    assert [f.error_type for f in pasta.failures] == ["LanguageModelResponseInvalidError"]
    assert pasta.verdicts["out_of_scope"] == 2


def test_triado_inalterado_nao_e_reenviado(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.triar("demo_a")
    env.model.requests.clear()
    relatorio = env.triar("demo_a")
    assert env.model.calls() == 0 and relatorio.folders[0].remaining == 0


def test_unknown_gap_sem_tipo_sugerido(env: TriageEnv) -> None:
    env.registrar("demo_a", {"README.md": "leia"})
    env.model.default(ModelRole.TRIAGE, triagem("gap"))
    pasta = env.triar("demo_a").folders[0]
    assert pasta.failures[0].error_type == "InvalidTriageError"


def test_licenca_restrita_gap_sem_resumo(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/x.md": "regra"}, license="unknown", status="pending")
    env.model.default(ModelRole.TRIAGE, triagem("gap"))
    pasta = env.triar("demo_a").folders[0]
    assert pasta.failures[0].error_type == "InvalidTriageError"
    assert "Licença restrita: sim" in env.model.requests[0].user_prompt


def test_artefato_grande_demais(env: TriageEnv) -> None:
    env.registrar("demo_a", {"skills/x/SKILL.md": "s", "skills/x/a.md": "a" * 200_000,
                             "skills/x/b.md": "b" * 100_000})  # fmt: skip
    pasta = env.triar("demo_a").folders[0]
    assert pasta.failures[0].error_type == "ArtifactTooLargeError"
    assert env.model.calls() == 0


# --- pastas e ambiente -------------------------------------------------------------------


def test_alias_inexistente(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    with pytest.raises(FolderNotFoundError):
        env.triar("nao_existe")


def test_pasta_nunca_inventariada(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES, inventariar=False)
    with pytest.raises(CurationNotInventoriedError, match="curation inventory demo_a"):
        env.triar("demo_a")
    assert env.model.calls() == 0


def test_all_isola_pasta_com_estado_corrompido_e_pula_ignore(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.registrar("demo_b", TRES)
    env.registrar("demo_c", TRES, status="ignore", inventariar=False)
    (env.registry.parent / "curation" / "demo_a" / "state.json").write_text("{", encoding="utf-8")
    relatorio = env.triar(None)
    assert [f.alias for f in relatorio.failures] == ["demo_a"]
    assert [p.alias for p in relatorio.folders] == ["demo_b"]
    assert relatorio.skipped == ["demo_c"]


def test_lock_ocupado(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    with env.store.lock("demo_a"), pytest.raises(CurationLockedError):
        env.triar("demo_a")
    assert env.model.calls() == 0


def test_cli_nao_verificado_falha_antes_de_chamar(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.model.ready_error = LanguageModelUntestedVersionError("2.9.0")
    with pytest.raises(LanguageModelUntestedVersionError):
        env.triar("demo_a")
    assert env.model.calls() == 0


def test_prompt_ausente_falha_antes_de_chamar(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    (env.project / "prompts" / "curation" / "judge.md").unlink()
    with pytest.raises(PromptSetError):
        env.triar("demo_a")
    assert env.model.calls() == 0


def test_logs_sem_conteudo_do_artefato(env: TriageEnv, caplog: pytest.LogCaptureFixture) -> None:
    """FR-034 (achado C1 da análise): conteúdo e resposta do modelo nunca vão para o log."""
    env.registrar("demo_a", {"a.md": "MARCADOR-DO-CONTEUDO"})
    env.model.default(ModelRole.TRIAGE, triagem(justification="MARCADOR-DA-RESPOSTA"))
    with caplog.at_level(logging.DEBUG):
        env.triar("demo_a")
    assert "triage_artifact" in caplog.text
    assert "MARCADOR-DO-CONTEUDO" not in caplog.text
    assert "MARCADOR-DA-RESPOSTA" not in caplog.text
    assert str(env.base) not in caplog.text


def test_estado_gravado_valido(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.triar("demo_a")
    documento = json.loads(
        (env.registry.parent / "curation" / "demo_a" / "state.json").read_text("utf-8")
    )
    assert documento["schema_version"] == "2"


# --- US2: rascunhos, similaridade e fusões -------------------------------------------------

ORIGINAL = """# Contract first

## When

- new project
- weak bar

## Steps

1. write the contract
2. wire gates
3. refuse to lower
"""
COPIA_TRADUZIDA = """# Contrato primeiro

## Quando

- projeto novo
- barra fraca

## Passos

1. escreva o contrato
2. ligue os gates
3. recuse rebaixar
"""
AUTORAL = {
    "kind": "rule",
    "name": "contrato-antes-do-codigo",
    "description": "Escreve a barra de qualidade antes de implementar.",
    "body": "# Contrato antes do código\n\nUm parágrafo próprio com a ideia sintetizada.\n",
}
COPIA = AUTORAL | {"body": COPIA_TRADUZIDA}
JUIZ_DERIVADA = {"is_derivative": True, "justification": "segue o original passo a passo"}


def _gap(**campos: object) -> dict[str, object]:
    return triagem("gap", **campos)


def test_gap_gera_rascunho_autoral(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/contrato.md": ORIGINAL})
    env.model.default(ModelRole.TRIAGE, _gap())
    env.model.default(ModelRole.DRAFT, AUTORAL)
    pasta = env.triar("demo_a").folders[0]
    assert (pasta.drafts, pasta.drafts_alerted) == (1, 0)
    estado = env.estado("demo_a")["rules/contrato.md"]
    assert estado["stage"] == "drafted"
    rascunho = env.drafts.load(estado["triage"]["draft_id"])
    assert rascunho is not None
    assert [(o.alias, o.path) for o in rascunho.origins] == [("demo_a", "rules/contrato.md")]
    assert rascunho.origins[0].sha256 == estado["sha256"]
    assert len(rascunho.checks) == 1 and not rascunho.similarity_alert
    assert env.model.calls(ModelRole.DRAFT) == 1 and env.model.calls(ModelRole.JUDGE) == 1


def test_copia_estrutural_regenera_uma_vez_e_alerta(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/contrato.md": ORIGINAL})
    env.model.default(ModelRole.TRIAGE, _gap())
    env.model.default(ModelRole.DRAFT, COPIA)
    pasta = env.triar("demo_a").folders[0]
    assert env.model.calls(ModelRole.DRAFT) == 2
    assert (pasta.drafts, pasta.drafts_alerted) == (1, 1)
    segunda = [r for r in env.model.requests if r.role is ModelRole.DRAFT][1]
    assert "Reescreva a partir das ideias" in segunda.user_prompt
    rascunho = env.drafts.list_pending()[0]
    assert len(rascunho.checks) == 2 and rascunho.similarity_alert
    assert rascunho.checks[0].structural_score >= 0.7


def test_juiz_sinaliza_e_regeneracao_resolve(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/contrato.md": ORIGINAL})
    env.model.default(ModelRole.TRIAGE, _gap())
    env.model.default(ModelRole.DRAFT, AUTORAL)
    env.model.script(ModelRole.JUDGE, "Contrato antes do código", JUIZ_DERIVADA, {
        "is_derivative": False, "justification": "agora é autoral"})  # fmt: skip
    pasta = env.triar("demo_a").folders[0]
    assert env.model.calls(ModelRole.DRAFT) == 2 and pasta.drafts_alerted == 0
    rascunho = env.drafts.list_pending()[0]
    assert [c.flagged for c in rascunho.checks] == [True, False]


def test_covered_e_fora_de_escopo_sem_rascunho(env: TriageEnv) -> None:
    escrever_item(env.project, "rule", "estilo", description="estilo")
    env.registrar("demo_a", {"rules/a.md": "a", "rules/b.md": "b"})
    env.model.script(ModelRole.TRIAGE, "rules/a.md", triagem("covered", covered_by=["rule/estilo"]))
    env.triar("demo_a")
    assert env.model.calls(ModelRole.DRAFT) == 0 and env.drafts.list_pending() == []


def test_fusao_com_item_do_acervo(env: TriageEnv) -> None:
    escrever_item(env.project, "rule", "estilo", description="estilo", corpo="REGRA-EXISTENTE\n")
    env.registrar("demo_a", {"rules/a.md": "a"})
    env.model.default(
        ModelRole.TRIAGE, _gap(merge_target={"kind": "library", "ref": "rule/estilo"})
    )
    env.triar("demo_a")
    rascunho = env.drafts.list_pending()[0]
    assert rascunho.merge_target is not None and rascunho.merge_target.ref == "rule/estilo"
    pedido = next(r for r in env.model.requests if r.role is ModelRole.DRAFT)
    assert "REGRA-EXISTENTE" in pedido.user_prompt


def test_fusao_com_rascunho_de_outra_pasta(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "a"})
    env.registrar("demo_b", {"rules/b.md": "b"})
    env.model.default(ModelRole.TRIAGE, _gap())
    env.triar("demo_a")
    existente = env.drafts.list_pending()[0]
    env.model.default(
        ModelRole.TRIAGE, _gap(merge_target={"kind": "draft", "ref": existente.draft_id})
    )
    env.triar("demo_b")
    pendentes = env.drafts.list_pending()
    assert len(pendentes) == 1
    assert [o.alias for o in pendentes[0].origins] == ["demo_a", "demo_b"]
    triagem_b = [r for r in env.model.requests if r.role is ModelRole.TRIAGE][-1]
    assert existente.draft_id in triagem_b.user_prompt
    assert "RASCUNHOS_NAO_CONFIAVEIS" in triagem_b.user_prompt
    assert existente.proposal.body not in triagem_b.user_prompt  # só id/tipo/nome/descrição


def test_rascunho_da_execucao_entra_no_indice_seguinte(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "a", "rules/b.md": "b"})
    env.model.default(ModelRole.TRIAGE, _gap())
    env.triar("demo_a")
    triagens = [r for r in env.model.requests if r.role is ModelRole.TRIAGE]
    assert "Nenhum rascunho pendente." in triagens[0].user_prompt
    assert "rascunho-de-teste" in triagens[1].user_prompt


def test_licenca_restrita_rascunho_so_ve_o_resumo(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "TEXTO-ORIGINAL-SECRETO"}, license="unknown",
                  status="pending")  # fmt: skip
    env.model.default(ModelRole.TRIAGE, _gap(ideas_summary="RESUMO-DAS-IDEIAS"))
    env.triar("demo_a")
    pedido = next(r for r in env.model.requests if r.role is ModelRole.DRAFT)
    assert "RESUMO-DAS-IDEIAS" in pedido.user_prompt
    assert "TEXTO-ORIGINAL-SECRETO" not in pedido.user_prompt


def test_rascunho_corrompido_para_antes_de_chamar(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "a"})
    area = env.registry.parent / "curation" / "_drafts"
    area.mkdir(parents=True)
    (area / "0123456789abcdef.json").write_text("{", encoding="utf-8")
    with pytest.raises(DraftStoreCorruptError, match="0123456789abcdef"):
        env.triar("demo_a")
    assert env.model.calls() == 0


def test_falha_no_rascunho_mantem_a_triagem(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "a"})
    env.model.default(ModelRole.TRIAGE, _gap())
    env.model.default(ModelRole.DRAFT, LanguageModelResponseInvalidError("x"))
    pasta = env.triar("demo_a").folders[0]
    estado = env.estado("demo_a")["rules/a.md"]
    assert estado["stage"] == "failed" and estado["triage"]["verdict"] == "gap"
    assert pasta.verdicts["gap"] == 1 and pasta.failures[0].error_type == (
        "LanguageModelResponseInvalidError"
    )


def test_rascunho_invalido_pelo_dominio(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "a"})
    env.model.default(ModelRole.TRIAGE, _gap())
    env.model.default(ModelRole.DRAFT, AUTORAL | {"kind": "unknown"})
    pasta = env.triar("demo_a").folders[0]
    assert pasta.failures[0].error_type == "InvalidTriageError"


# --- US3: teto, retomada, falhas consecutivas ---------------------------------------------

CINCO = {f"{n}.md": f"# {n}" for n in "abcde"}


def test_teto_de_chamadas_e_retomada(env: TriageEnv) -> None:
    env.registrar("demo_a", CINCO)
    relatorio = env.triar("demo_a", max_calls=2)
    assert (relatorio.calls, relatorio.stop_reason) == (2, "budget")
    assert relatorio.folders[0].remaining == 3
    enviados = {r.user_prompt.split("Artefato: ")[1].split(" ")[0] for r in env.model.requests}
    assert enviados == {"a.md", "b.md"}
    env.model.requests.clear()
    retomada = env.triar("demo_a", max_calls=10)
    retomados = [r.user_prompt.split("Artefato: ")[1].split(" ")[0] for r in env.model.requests]
    assert retomados == ["c.md", "d.md", "e.md"]  # nada reenviado (SC-002)
    assert retomada.stop_reason == "done"


def test_teto_soma_pastas_no_all(env: TriageEnv) -> None:
    env.registrar("demo_a", {"a.md": "a", "b.md": "b"})
    env.registrar("demo_b", {"a.md": "a", "b.md": "b"})
    relatorio = env.triar(None, max_calls=3)
    assert relatorio.calls == 3 and env.model.calls() == 3
    assert [p.remaining for p in relatorio.folders] == [0, 1]


def test_teto_nunca_ultrapassado_com_rascunho(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "a", "rules/b.md": "b"})
    env.model.default(ModelRole.TRIAGE, triagem("gap"))
    relatorio = env.triar("demo_a", max_calls=4)
    # triagem de a (1) → rascunho precisaria de 4 → fica triada sem rascunho e para
    assert env.model.calls() <= 4 and relatorio.stop_reason == "budget"
    estado = env.estado("demo_a")["rules/a.md"]
    assert estado["stage"] == "triaged" and estado["triage"]["draft_id"] is None
    env.model.requests.clear()
    env.triar("demo_a", max_calls=10)
    papeis = [r.role for r in env.model.requests]
    assert papeis[0] is ModelRole.DRAFT  # retomada só rascunha, sem triar de novo
    assert env.estado("demo_a")["rules/a.md"]["stage"] == "drafted"


def test_teto_de_custo_repassa_o_restante(env: TriageEnv) -> None:
    env.registrar("demo_a", CINCO)
    relatorio = env.triar("demo_a", max_cost_usd=Decimal("0.025"))
    orcamentos = [r.max_budget_usd for r in env.model.requests]
    assert orcamentos == [Decimal("0.025"), Decimal("0.015"), Decimal("0.005")]
    assert relatorio.stop_reason == "budget"


def test_falhas_consecutivas_param_e_invalida_nao_conta(env: TriageEnv) -> None:
    env.registrar("demo_a", {f"{n}.md": n for n in "abcdefg"})
    env.model.script(ModelRole.TRIAGE, "a.md", LanguageModelResponseInvalidError("x"))
    env.model.default(ModelRole.TRIAGE, LanguageModelUnavailableError("fora do ar"))
    relatorio = env.triar("demo_a", max_consecutive_failures=3)
    assert relatorio.stop_reason == "consecutive_failures"
    assert env.model.calls() == 4  # a (inválida, não conta) + 3 indisponíveis
    etapas = {p: s["stage"] for p, s in env.estado("demo_a").items()}
    assert list(etapas.values()).count("failed") == 4 and etapas["g.md"] == "pending"


def test_tentativas_esgotadas_e_retry_failed(env: TriageEnv) -> None:
    env.registrar("demo_a", {"a.md": "a"})
    env.model.default(ModelRole.TRIAGE, LanguageModelResponseInvalidError("x"))
    for _ in range(3):
        env.triar("demo_a")
    assert env.estado("demo_a")["a.md"]["attempts"] == 3
    env.model.requests.clear()
    env.triar("demo_a")
    assert env.model.calls() == 0
    env.triar("demo_a", retry_failed=True)
    assert env.model.calls() == 1


def test_interrupcao_preserva_o_estado_anterior(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    env.model.script(ModelRole.TRIAGE, "b.md", KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        env.triar("demo_a")
    etapas = {p: s["stage"] for p, s in env.estado("demo_a").items()}
    assert etapas == {"a.md": "triaged", "b.md": "pending", "c.md": "pending"}


# --- US4: mudar prompt ou critérios invalida vereditos -----------------------------------


def _mudar_criterios(env: TriageEnv) -> None:
    arquivo = env.project / "prompts" / "curation" / "criteria.md"
    arquivo.write_text(arquivo.read_text(encoding="utf-8") + "\nNovo critério.\n", "utf-8")


def test_impressao_digital_gravada_e_mudanca_reabre(env: TriageEnv) -> None:
    env.registrar("demo_a", {"rules/a.md": "a", "rules/b.md": "b", "rules/c.md": "c"})
    env.model.script(ModelRole.TRIAGE, "rules/b.md", triagem("gap"))
    env.model.script(ModelRole.TRIAGE, "rules/c.md", LanguageModelResponseInvalidError("x"))
    env.triar("demo_a")
    antes = env.estado("demo_a")
    impressao = antes["rules/a.md"]["triage"]["prompt_fingerprint"]
    assert antes["rules/b.md"]["triage"]["prompt_fingerprint"] == impressao
    rascunho = env.drafts.load(antes["rules/b.md"]["triage"]["draft_id"])
    assert rascunho is not None and rascunho.prompt_fingerprint == impressao
    # revisado pela 012 (simulado): nunca volta
    arquivo = env.registry.parent / "curation" / "demo_a" / "state.json"
    documento = json.loads(arquivo.read_text("utf-8"))
    documento["artifacts"]["rules/a.md"]["stage"] = "reviewed"
    arquivo.write_text(json.dumps(documento), encoding="utf-8")
    _mudar_criterios(env)
    env.model.requests.clear()
    env.model.script(ModelRole.TRIAGE, "rules/c.md", triagem())
    env.triar("demo_a")
    triados = sorted(
        r.user_prompt.split("Artefato: ")[1].split(" ")[0]
        for r in env.model.requests
        if r.role is ModelRole.TRIAGE
    )
    assert triados == ["rules/b.md", "rules/c.md"]
    depois = env.estado("demo_a")
    assert depois["rules/b.md"]["triage"]["prompt_fingerprint"] != impressao
    assert depois["rules/a.md"]["triage"]["prompt_fingerprint"] == impressao


def test_prompt_vazio_exit_antes_de_chamar(env: TriageEnv) -> None:
    env.registrar("demo_a", TRES)
    (env.project / "prompts" / "curation" / "draft.md").write_text(" \n", encoding="utf-8")
    with pytest.raises(PromptSetError, match="draft.md"):
        env.triar("demo_a")
    assert env.model.calls() == 0
