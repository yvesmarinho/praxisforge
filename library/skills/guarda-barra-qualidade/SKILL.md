---
name: guarda-barra-qualidade
description: Define a barra de qualidade do projeto como contrato escrito e verificável (CONSTRAINTS.md) e impede que o agente a rebaixe para chegar ao verde — supressões novas, testes pulados ou apagados, asserções removidas, stubs, limites editados para baixo. Use quando não há barra escrita, quando pedirem para "definir padrões"/"quality gates", ou quando um agente estiver silenciando verificações para passar.
license: MIT
metadata:
  version: '1.0.0'
  sources: [agent-skills-constraints]
  authored: false
---
<!-- Criado em: 25/09/2026 09:45 -->
<!-- Modificado em: 25/09/2026 09:46 -->

# Guarda da barra de qualidade

O agente escreve mais código do que alguém consegue ler. O julgamento de "bom o bastante para
entregar" precisa estar escrito, com números e com o comando que dá o veredito — e o agente não
pode mexer nele para fazer a mudança passar.

Não use em scripts descartáveis, spikes ou quando o projeto já tem um `CONSTRAINTS.md` que o
usuário não quer mudar (nesse caso, leia e siga).

## 1. Detectar antes de perguntar

Leia antes de qualquer pergunta: linguagem e stack (`pyproject.toml`, `package.json`...), runner
de testes, linters, cobertura atual (rode a suíte uma vez), CI e arquivos do agente
(`CLAUDE.md`, `AGENTS.md`). Relate o que encontrou em duas linhas.

## 2. No máximo quatro perguntas, cada uma com padrão

Uma pergunta por vez; "não sei" é resposta válida e usa o padrão.

1. Além do piso, quais dimensões aplicar (cobertura, segurança, performance, acessibilidade,
   camadas)? Padrão: cobertura e segurança.
2. Falha no meio da tarefa bloqueia ou avisa? Padrão: bloqueia no piso, avisa no resto.
3. Há metas numéricas ou devo medir o estado atual e segurar? Padrão: medir e segurar (catraca).
4. Qual a verificação mais lenta tolerada ao fim da tarefa? Padrão: ~90 s.

Em execução não interativa (CI, loop autônomo), não pergunte: aplique só o piso e registre o
restante como pendência para um humano.

## 3. Escrever `CONSTRAINTS.md` na raiz

- **Piso** (sempre, sem instalar nada): nenhuma supressão nova (`# noqa`, `# type: ignore`,
  `eslint-disable`, `@ts-ignore`); nenhum stub não implementado nem `except`/`catch` vazio;
  nenhum teste pulado ou apagado sem motivo no commit; nenhum secret; este arquivo não é
  afrouxado para uma mudança passar.
- **Dimensões com número**: tabela `dimensão | regra | comando | quando roda`. Número sem comando
  é aspiração, não restrição.
- **Medido, ainda não aplicado**: valor de hoje + direção ("não pode cair").
- **Exceções**: regra, caminho, motivo, dono e validade (padrão: 90 dias).

Todo número vem com o motivo ao lado. Aponte o arquivo no `CLAUDE.md`/`AGENTS.md`: "Leia
`CONSTRAINTS.md` antes de escrever código. Não o enfraqueça para uma mudança passar."

## 4. Custo decide onde cada verificação roda

| Fase | O que roda | Orçamento |
|------|------------|-----------|
| A cada edição | tipos, lint, secrets, piso — só o arquivo alterado | poucos segundos |
| Fim da tarefa | testes relacionados, cobertura das linhas alteradas | ~90 s |
| Revisão/CI | tudo, mais a guarda da barra | minutos |

Restrinja ao diff. Verificação lenta no ciclo de edição acaba desligada — e uma barreira
desligada é pior do que nenhuma, porque a barra continua parecendo existir. Use as ferramentas
de fato do ecossistema em vez de escrever um checador próprio.

## 5. Guardar a própria barra

Diante de uma verificação vermelha, o agente tende ao caminho mais barato até o verde. Na
revisão, procure no `git diff`:

1. **Limite mexido**: orçamento reduzido, severidade rebaixada, verificação removida.
2. **Teste facilitado**: `skip` novo, arquivo de teste apagado, asserções retiradas.
3. **Checador silenciado**: supressões novas, sobretudo as que tiram código da cobertura ou
   escondem achados de segurança (`pragma: no cover`, `nosec`, `nosemgrep`).
4. **Trabalho inacabado**: stub que lança erro, `except` vazio, `TODO` no lugar da implementação.
5. **Exceção nova** que ninguém discutiu.

Apertar a barra é silencioso; afrouxar deve ser ruidoso. `CONSTRAINTS.md` alterado no mesmo
commit da funcionalidade que estava falhando é sinal de alerta.

## 6. Nem toda verificação vale o mesmo

Pergunte: o agente consegue passar nesta verificação com código que não funciona?

- **Externa** (base de vulnerabilidades, WCAG, navegador real): não dá para argumentar.
- **Do projeto** (regras de lint, fronteiras de camada): um humano é dono do arquivo.
- **Da própria suíte**: a mais útil e a única realmente circular.

Garanta ao menos uma verificação externa.

## 7. Catraca quando não há número

Impor 80% de cobertura num código com 62% gera build vermelho eterno e um time que aprende a
ignorar vermelho. Registre o valor de hoje, compare sempre com ele e recuse piora; quando
melhorar, atualize o registro.

## Verificação

- [ ] `CONSTRAINTS.md` existe e todo número tem motivo.
- [ ] O piso é aplicado e passa no código atual sem mudanças.
- [ ] Toda dimensão escolhida tem ferramenta instalada e comando que roda hoje.
- [ ] A fase rápida fica em poucos segundos.
- [ ] Há ao menos uma verificação externa.
- [ ] Métricas só medidas têm valor atual e direção.
- [ ] Exceções têm dono e validade.
- [ ] `CLAUDE.md`/`AGENTS.md` aponta para o arquivo.

## Atribuição

Obra derivada (tradução e adaptação para pt-BR) da skill `constraint-driven-development` de
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills), commit `d2c37ef`.
Copyright (c) 2025 Addy Osmani, licença MIT — texto integral em
[LICENSE.agent-skills](LICENSE.agent-skills).
