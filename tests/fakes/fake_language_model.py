# -*- coding: utf-8 -*-
"""
NOME: fake_language_model.py
TITULO: LanguageModel falso para os testes — respostas roteirizadas por papel e artefato
DATA: 28/09/2026 15:56
MODIFICADO: 28/09/2026 15:56
VERSÃO: 0.1.0
DEPEND: praxisforge.application.ports
HISTÓRICO:
    - 28/09/2026 15:56: criação (T020, feature 011)
STATUS: DEV
"""

from collections.abc import Mapping
from decimal import Decimal

from praxisforge.application.ports import LanguageModel, ModelReply, ModelRequest, ModelRole

Resposta = Mapping[str, object] | BaseException

TRIAGEM_OUT: dict[str, object] = {
    "verdict": "out_of_scope",
    "justification": "não é conhecimento curável",
    "covered_by": [],
    "merge_target": None,
    "suggested_kind": None,
    "ideas_summary": None,
}
RASCUNHO_OK: dict[str, object] = {
    "kind": "skill",
    "name": "rascunho-de-teste",
    "description": "Rascunho autoral de teste.",
    "body": "# Ideia\n\nParágrafo único com a ideia sintetizada.\n",
}
JUIZ_OK: dict[str, object] = {"is_derivative": False, "justification": "estrutura própria"}


class FakeLanguageModel(LanguageModel):
    """
    Modelo falso: nunca chama rede nem processo.

    Respostas roteirizadas por (papel, marcador): o marcador é um texto que precisa aparecer no
    prompt do usuário (ex.: o caminho do artefato). Cada roteiro é uma fila; o último item se
    repete. Sem roteiro, usa a resposta padrão do papel.
    """

    def __init__(self, cost: Decimal | None = Decimal("0.01")) -> None:
        self.cost = cost
        self.requests: list[ModelRequest] = []
        self.ready_error: Exception | None = None
        self._roteiros: dict[tuple[ModelRole, str], list[Resposta]] = {}
        self._padrao: dict[ModelRole, Resposta] = {
            ModelRole.TRIAGE: TRIAGEM_OUT,
            ModelRole.DRAFT: RASCUNHO_OK,
            ModelRole.JUDGE: JUIZ_OK,
        }

    def script(self, role: ModelRole, marker: str, *responses: Resposta) -> None:
        """Enfileira respostas para chamadas do papel cujo prompt contém o marcador."""
        self._roteiros[(role, marker)] = list(responses)

    def default(self, role: ModelRole, response: Resposta) -> None:
        """Troca a resposta padrão de um papel."""
        self._padrao[role] = response

    def calls(self, role: ModelRole | None = None) -> int:
        """Número de chamadas feitas (de um papel ou no total)."""
        return sum(1 for r in self.requests if role is None or r.role is role)

    def check_ready(self) -> None:
        """Ver LanguageModel.check_ready."""
        if self.ready_error is not None:
            raise self.ready_error

    def complete(self, request: ModelRequest) -> ModelReply:
        """Ver LanguageModel.complete."""
        self.requests.append(request)
        resposta = self._padrao[request.role]
        for (papel, marcador), fila in self._roteiros.items():
            if papel is request.role and marcador in request.user_prompt:
                resposta = fila.pop(0) if len(fila) > 1 else fila[0]
                break
        if isinstance(resposta, BaseException):
            raise resposta
        return ModelReply(payload=dict(resposta), cost_usd=self.cost, model=f"fake-{request.model}")
