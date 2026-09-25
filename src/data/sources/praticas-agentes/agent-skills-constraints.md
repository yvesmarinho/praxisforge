---
schema_version: "3"
origin: https://github.com/addyosmani/agent-skills
author: Addy Osmani
date: "2026-09-25"
license: MIT
relevance: barra de qualidade escrita e verificável que o agente não pode rebaixar para chegar ao verde (supressões, testes pulados, limites editados)
status: active
---
<!-- Criado em: 25/09/2026 09:45 -->
<!-- Modificado em: 25/09/2026 13:06 -->

# Constraint-driven development (addyosmani/agent-skills)

Skill `constraint-driven-development` da coleção de 25 skills de engenharia publicada por Addy
Osmani (licença MIT, arquivo `LICENSE` presente). Versão consultada: commit `d2c37ef` do fork
local. As demais skills da coleção (TDD, revisão, git, arquitetura, spec) se sobrepõem às regras
globais do curador e não foram extraídas nesta curadoria.

## Síntese

A fonte parte de uma constatação: o agente escreve mais código do que alguém consegue ler, então
o julgamento de qualidade precisa sair da cabeça do revisor e virar verificações com números,
escritas num arquivo que sobrevive à sessão.

1. **Detectar antes de perguntar**: ler stack, runner de testes, linters, cobertura atual e CI
   antes de qualquer pergunta; perguntar só o que falta, no máximo quatro perguntas, cada uma com
   um valor padrão.
2. **Contrato escrito** (`CONSTRAINTS.md` na raiz): um piso sempre aplicado (sem novas
   supressões, sem stubs não implementados, sem testes pulados ou apagados sem motivo, sem
   secrets, o próprio arquivo não é afrouxado), dimensões com número **e** comando que dá o
   veredito, métricas apenas medidas, e exceções com dono e validade.
3. **Custo define o lugar**: verificações rápidas a cada edição, testes relacionados ao fim da
   tarefa, o resto na revisão/CI; sempre restritas ao diff. Verificação lenta no ciclo de edição
   acaba desligada.
4. **Guardar a própria barra**: no diff, procurar limite alterado, teste enfraquecido, checador
   silenciado, trabalho inacabado e exceção nova. Apertar a barra é silencioso; afrouxar deve ser
   ruidoso.
5. **Nem toda verificação é circular**: externas (base de vulnerabilidades, WCAG) > do projeto
   (regras de lint, camadas) > a própria suíte. Exigir ao menos uma externa.
6. **Catraca** quando não há número: registrar o valor de hoje e recusar piora, em vez de impor
   uma meta que o código já falha.

## Uso no praxisforge

Origem da skill `guarda-barra-qualidade`. A skill segue a estrutura da original passo a passo e
é tradução adaptada, portanto **obra derivada**: carrega o aviso de copyright e o texto da licença
MIT (`skills/guarda-barra-qualidade/LICENSE.agent-skills`), não só a citação.
