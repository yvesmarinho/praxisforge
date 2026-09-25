---
name: diretrizes-codificacao
description: Diretrizes de comportamento para escrever, revisar ou refatorar código sem os erros típicos de LLMs — explicitar premissas, preferir a solução mais simples, fazer mudanças cirúrgicas e trabalhar contra critérios de sucesso verificáveis. Use em qualquer tarefa de código que não seja trivial.
license: MIT
metadata:
  version: '1.0.0'
  sources: [karpathy-guidelines]
  authored: false
---
<!-- Criado em: 24/09/2026 17:22 -->
<!-- Modificado em: 24/09/2026 17:22 -->

# Diretrizes de codificação

Estas diretrizes priorizam **cautela sobre velocidade**. Em tarefas triviais (typo, renomear uma
variável local), use o bom senso e não transforme a tarefa em cerimônia.

## 1. Pensar antes de codificar

- Declare as premissas que você está assumindo. Se houver incerteza real, pergunte.
- Se o pedido admite mais de uma interpretação razoável, apresente as opções em vez de escolher
  uma em silêncio.
- Se existe um caminho mais simples do que o pedido, diga isso antes de implementar.
- Se algo está confuso, pare, diga exatamente o que não ficou claro e pergunte.

## 2. Simplicidade primeiro

- Escreva o mínimo que resolve o pedido; nada especulativo.
- Nada de funcionalidade, configuração ou "flexibilidade" que ninguém pediu.
- Nada de abstração para código usado em um único lugar.
- Nada de tratamento de erro para cenários impossíveis.
- Pergunta de controle: um engenheiro sênior acharia isto complicado demais? Se sim, simplifique.

## 3. Mudanças cirúrgicas

- Toque só no necessário. Não "melhore" código, comentários ou formatação vizinhos, nem refatore
  o que não está quebrado.
- Mantenha o estilo existente, mesmo que você faria diferente.
- Código morto que já existia: mencione, não apague.
- Imports, variáveis e funções que a **sua** mudança deixou sem uso: remova.
- Teste final: cada linha alterada precisa ser rastreável ao pedido.

## 4. Execução orientada a objetivo

Transforme o pedido em um critério verificável antes de implementar:

| Pedido | Critério verificável |
|---|---|
| "Adicionar validação" | testes para entradas inválidas, depois fazê-los passar |
| "Corrigir o bug" | teste que reproduz a falha, depois fazê-lo passar |
| "Refatorar X" | a suíte passa antes e depois, sem mudar comportamento |

Em tarefas de várias etapas, declare um plano curto no formato `passo → verificação`:

```text
1. <passo> → verificar: <como saber que deu certo>
2. <passo> → verificar: <como saber que deu certo>
```

Critérios fortes permitem iterar sozinho até o fim; critérios fracos ("fazer funcionar") obrigam a
pedir esclarecimento a cada passo.

## Sinais de que está funcionando

- Diffs menores, sem mudanças fora do pedido.
- Menos retrabalho por excesso de complexidade.
- Perguntas de esclarecimento chegam **antes** da implementação, não depois dos erros.

---

Síntese autoral das diretrizes publicadas por forrestchang em
[andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) (MIT), derivadas
das observações de Andrej Karpathy sobre erros de LLMs ao codificar.
