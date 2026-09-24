---
schema_version: "2"
origin: https://github.com/forrestchang/andrej-karpathy-skills
author: forrestchang
date: "2026-09-24"
license: MIT
relevance: diretrizes de comportamento que reduzem erros comuns de LLMs ao codificar (suposições ocultas, excesso de complexidade, mudanças fora do escopo, critérios de sucesso fracos)
status: active
extract_policy: summary
extract_scope: docs
---
<!-- Criado em: 24/09/2026 17:22 -->
<!-- Modificado em: 24/09/2026 17:22 -->

# Karpathy guidelines (forrestchang/andrej-karpathy-skills)

Plugin/skill de Claude Code publicado por forrestchang, com as observações de Andrej Karpathy sobre
os erros recorrentes de LLMs ao escrever código. A licença MIT está declarada no README, e o
repositório não traz arquivo `LICENSE`. Versão consultada: commit `2c60614` do fork local,
plugin `1.0.0`.

## Síntese

A fonte organiza as diretrizes em quatro princípios e assume que eles favorecem cautela sobre
velocidade; tarefas triviais ficam a critério do bom senso.

1. **Pensar antes de codificar**: explicitar premissas, apresentar as interpretações possíveis em
   vez de escolher uma em silêncio, apontar alternativas mais simples e parar para perguntar quando
   algo não está claro.
2. **Simplicidade primeiro**: o mínimo de código que resolve o pedido, sem funcionalidades,
   abstrações ou configurações especulativas. O teste proposto é perguntar se um engenheiro
   sênior acharia a solução complicada demais.
3. **Mudanças cirúrgicas**: tocar só o necessário, manter o estilo existente e não refatorar
   vizinhança. Código morto que já existia é apenas mencionado; órfãos criados pela própria
   mudança são removidos. Toda linha alterada deve ser rastreável ao pedido.
4. **Execução orientada a objetivo**: transformar pedidos vagos em critérios verificáveis (por
   exemplo, "corrigir o bug" vira "teste que reproduz, depois passar") e declarar o plano como
   passos com verificação. A fonte observa que critérios fortes permitem iterar com autonomia.

## Uso no praxisforge

Origem da skill `diretrizes-codificacao`. As mesmas diretrizes já estão nas regras globais do
curador; a skill as leva para projetos e ferramentas que não carregam essas regras.
