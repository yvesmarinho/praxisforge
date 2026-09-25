<!-- Criado em: 25/09/2026 10:35 -->
<!-- Modificado em: 25/09/2026 11:28 -->

# Debate: curadoria automatizada

## A proposta

Tirar a decisão do que analisar e trazer para o projeto das mãos de quem conduz a sessão:

1. O código analisa a pasta.
2. Gera um JSON com os dados colhidos.
3. O código executa o `claude` CLI com um prompt de curadoria pré-existente.
4. O resultado do prompt é salvo em `skills/`.

**Origem do debate:** na curadoria do `agent_skills`, só as 25 skills foram consideradas e só uma
foi extraída. Commands, agents, hooks, references, rules e o `CLAUDE.md` do repositório ficaram de
fora sem que isso fosse registrado.

## Avaliação

A proposta é melhor do que o processo manual. Mas dois pontos precisam mudar: onde o resultado vai
parar e quem dá a palavra final.

### O que a proposta resolve

O problema não foi julgamento ruim sobre o que foi lido. Foi a **omissão silenciosa**: partes do
repositório nem chegaram a ser abertas.

- **Cobertura garantida pelo código.** O inventário lista *todos* os artefatos. Nada some porque
  alguém decidiu, sozinho, olhar só `skills/`.
- **Repetível.** O mesmo prompt vale para as 55 pastas, em vez de depender da sessão.
- **Auditável.** O JSON de entrada e a resposta ficam guardados, e dá para saber por que algo entrou
  ou ficou de fora.
- **Escala.** Fazer 55 pastas à mão, uma conversa por pasta, não é viável.

### Onde há discordância

**1. O julgamento não sai do processo, só muda de lugar.** Ele sai de quem conduz a sessão e vai
para o prompt. O ganho é que passa a estar **escrito e versionado**. A qualidade depende de o prompt
receber o contexto certo: para comparar com as regras globais, ele precisa ler o `CLAUDE.md`
global inteiro, e não só as descrições das skills.

**2. Gravar direto em `skills/` é o ponto fraco.** Isso pula três proteções que o projeto já tem:

- **Política de licença.** O LLM pode colar trecho literal de uma fonte `summary`. Quem garante o
  `extract_policy` tem que ser o código, não o prompt.
- **Proveniência.** Toda skill precisa de uma fonte registrada em `src/data/sources/`. O pipeline
  teria que gerar as duas coisas, e `skills validate` teria que rodar antes de qualquer coisa ser
  aceita.
- **Decisão humana.** Uma skill ruim publicada no global afeta todos os projetos.

→ O LLM grava **propostas** numa área de staging (algo como `curation/<alias>/`). Só o aceite do
curador leva a proposta para `skills/`.

**3. Segurança: conteúdo de terceiros entrando num agente.** Os forks são repositórios de outras
pessoas. Um README ou SKILL.md pode trazer instruções como "ignore o anterior e rode X". Com o
`claude` rodando com ferramentas liberadas (Bash, Write), isso é *prompt injection* com acesso à
máquina.

→ A chamada ao LLM sai **sem ferramentas**, com texto entrando e JSON saindo, e **quem grava os
arquivos é o código**. Isso também deixa a saída validável por schema.

**4. Tamanho e custo.** O `agent-skills` inteiro tem dezenas de milhares de linhas. Mandar tudo num
prompt só estoura o contexto ou dilui a atenção.

→ Um prompt por artefato (ou por grupo pequeno), mais um passo final que junta tudo.

**5. Não determinismo.** A mesma entrada pode render classificações diferentes em cada execução.
Isso não é grave se houver revisão humana, mas é mais um motivo para o LLM não gravar direto.

## Fluxo proposto

| Etapa | Quem executa | O que faz | Saída |
|-------|--------------|-----------|-------|
| 1. Inventário | código, sem LLM | varre a pasta e lista cada artefato: tipo (skill, command, agent, hook, rule, reference, doc), caminho, hash, tamanho e licença | manifesto JSON versionado, determinístico |
| 2. Triagem | LLM, sem ferramentas | por artefato: recebe o conteúdo, as regras globais e as skills existentes; devolve veredito (coberto / lacuna / fora de escopo), justificativa e rascunho quando for lacuna | propostas no staging |
| 3. Revisão | curador | tabela com todos os artefatos e seus vereditos; aprova ou descarta. **Todo artefato precisa ter veredito registrado** | decisões registradas |
| 4. Promoção | código | o que foi aprovado vira fonte + skill; `sources validate`, `skills validate` e `catalog`; PR | `src/data/sources/` + `skills/` |

**Resumo:** o código garante que nada fica de fora, o LLM faz a leitura pesada e o curador decide.

## Perguntas em aberto

1. **Commands, agents e hooks entram?** Se entrarem, o praxisforge precisa de bibliotecas além de
   `skills/` (ex.: `commands/`, `agents/`, com publicação em `~/.claude/commands` e
   `~/.claude/agents`). É uma decisão anterior ao pipeline.
2. **`claude -p` ou a API da Anthropic direto?** O CLI é mais simples e usa a assinatura. A API dá
   controle fino sobre ferramentas (nenhuma), schema de saída e custo. Para um passo sem ferramentas
   e com saída estruturada, a API é a opção indicada.
3. **O veredito de uma pasta vence?** Se o fork receber commits novos, o `scan` já volta a pasta para
   `in_curation`. A nova triagem deveria rodar só nos artefatos cujo hash mudou.

## Licença: "criar uma versão" em vez de copiar

> Orientação geral, não parecer jurídico.

### O princípio

O direito autoral protege a **expressão** (texto, estrutura, sequência, seleção), e **não ideias,
técnicas ou métodos**.

- **Síntese das ideias.** Entender o método e escrever do próprio jeito, com estrutura própria,
  combinando fontes. É uso de ideias e, em geral, não fere licença nenhuma. Citar a fonte continua
  sendo boa prática e dá rastreabilidade.
- **Paráfrase próxima.** Seguir o original seção por seção, com os mesmos exemplos e tabelas,
  trocando as palavras ou traduzindo. Tende a ser **obra derivada**, que depende da licença.
  **Tradução é o exemplo clássico de obra derivada.**

### Por licença

| Licença | Obra derivada permitida? | Condição |
|---------|--------------------------|----------|
| MIT, BSD, Apache-2.0 | Sim | manter o aviso de copyright e licença (Apache: indicar as mudanças) |
| GPL-3.0 | Sim | a derivada sai sob GPL também |
| Elastic-2.0 | Restrita | proíbe certos usos (ex.: oferecer como serviço gerenciado) |
| Sem licença (`unknown`) | **Não** | todos os direitos reservados; só dá para usar as ideias |

### Caso real: `guarda-barra-qualidade`

A skill segue a `constraint-driven-development` quase passo a passo e traduz o conteúdo: é **obra
derivada**. Como a fonte é MIT, isso é permitido, mas exige o aviso de copyright, e citar a fonte
não basta. A skill foi corrigida em 25/09/2026: seção "Atribuição" e texto integral da licença em
`skills/guarda-barra-qualidade/LICENSE.agent-skills`.

### Impacto no pipeline

- O LLM tende a parafrasear de perto: pedir para ele "criar uma versão" costuma gerar uma derivada,
  não uma síntese.
- O `extract_policy` precisa distinguir três níveis: **só ideias** (qualquer licença), **derivada**
  (licença permissiva + aviso) e **literal** (`verbatim`).
- Para fontes `link`/`unknown`, o prompt recebe só o resumo das ideias, não o texto original, para
  não gerar paráfrase.
- Um teste de similaridade entre a proposta e o original (sobreposição de trechos e de estrutura)
  sinaliza uma "síntese" que na verdade é derivada.
- A promoção (etapa 4) exige aviso e licença na pasta da skill sempre que o veredito for "derivada".

## Próximo passo

Se o desenho for aceito, ele vira uma feature do SpecKit (`/speckit-specify`). As respostas às
perguntas em aberto entram no `/speckit-clarify`.

## Questionário — decisões pendentes

Responda abaixo de cada pergunta. As opções servem de ponto de partida; escrever outra resposta é
válido. As marcadas com ★ bloqueiam a spec.

### A. Escopo do que é curado

**A1 ★. Quais tipos de artefato entram na curadoria?** Opções: só skills · skills + references
(como arquivos de apoio) · também commands, agents, hooks e rules.

> Resposta: todos os recursos necessários ao skill curado. (skills + references + commands + agents + hooks + rules)

**A2 ★. Se commands/agents/hooks/rules entram, o praxisforge ganha bibliotecas próprias**
(`commands/`, `agents/`, ...) **com publicação em `~/.claude/*`, ou eles são convertidos em skills?**

> Resposta: o que ficou decidio em ADR é que os todo o resultado da execução do praxisforge fica nesse repositório.

**A3. `CLAUDE.md`/`AGENTS.md` de terceiros viram o quê?** Opções: fonte de ideias para o CLAUDE.md
global · skill · só registro de fonte.

> Resposta: o conteúdo dos dois arquivos devem ser armazenados em README ou outro arquivo que será usado como index do conteúdo.

**A4. Temas fora do seu trabalho (ex.: web performance, frontend) são descartados automaticamente
ou vão para revisão com veredito "fora de escopo"?**

> Resposta: devem ser curados. o objetivo do projeto é uma base de conhecimento agnóstico.

### B. Inventário (etapa 1)

**B1. Onde fica o manifesto do inventário?** Opções: versionado no repo (atenção: o repo é
público, então sem caminhos absolutos) · fora do repo, junto do registro
(`~/.config/praxisforge/`).

> Resposta:junto do registro para garantir idempotencia

**B2. Como classificar o tipo de cada artefato?** Opções: por convenção de caminho (`skills/*/SKILL.md`,
`.claude/commands/*.md`...) · por conteúdo · convenção com fallback para "desconhecido" enviado
à revisão.

> Resposta: criar uma pasta com um nome mais apropriado, que contenha sub-pastas por tipo de agente contendo todos os arquivos.

**B3. Arquivos grandes, binários ou gerados (ex.: `graphify-out/`, `node_modules/`) são ignorados por
lista fixa, por `.gitignore` da pasta ou por limite de tamanho?**

> Resposta: sim

### C. Triagem com LLM (etapa 2)

**C1 ★. `claude -p` (assinatura, mais simples) ou a API da Anthropic (controle de ferramentas,
schema e custo)?**

> Resposta: cli

**C2. Qual modelo? Um só ou um mais barato para a triagem e outro para o rascunho?**

> Resposta: um mais barato para a triagem e outro para o rascunho

**C3. Qual o contexto de comparação enviado junto com o artefato?** Opções: CLAUDE.md global +
regras por linguagem · + skills já existentes · + vault `claude_memory`.

> Resposta: gere uma nova proposta não utilizando o CLAUDE.nd global. todo recurso deve estar dentro do repo.

**C4. Qual a granularidade?** Opções: um prompt por artefato · por grupo pequeno · por pasta inteira.

> Resposta: prompt por artefato

**C5. Há um teto de custo por pasta ou por execução? Qual o comportamento ao atingir o teto
(parar, pular, pedir confirmação)?**

> Resposta: parar e salvar onde parou, talvez um arquivo de estado. aceito proposta sua

**C6. O prompt de curadoria fica versionado no repo? Mudar o prompt invalida os vereditos
anteriores?**

> Resposta: sim, faz parte do código/processo do praxisforge.

### D. Licença e originalidade

**D1 ★. Aceita os três níveis de extração: "só ideias" (qualquer licença), "derivada" (licença
permissiva + aviso) e "literal" (`verbatim`)? Isso muda o `extract_policy` e o
`source-schema` (breaking → v3).**

> Resposta: só ideias

**D2. Para fontes `link`/`unknown`, o LLM recebe só um resumo das ideias, e não o texto original?**

> Resposta: sim

**D3. Teste de similaridade: vale implementar? Qual limiar marca uma "síntese" como derivada?**

> Resposta: sim

**D4. Skills derivadas podem ser publicadas no escopo global, ou só as de "só ideias"/autorais?**

> Resposta: nada no escopo global. proponha uma estrutura no repo.

### E. Staging e revisão (etapa 3)

**E1. Onde fica o staging?** Opções: `curation/<alias>/` no repo (versionado ou no `.gitignore`) ·
fora do repo.

> Resposta: curation/<alias>/

**E2. Em que formato você revisa?** Opções: tabela Markdown gerada · comando interativo na CLI
(`praxisforge curation review`) · página HTML.

> Resposta: cli

**E3. O veredito "coberto" ou "fora de escopo" precisa da sua aprovação, ou só os de "lacuna"?**

> Resposta: lacuna

**E4. Onde ficam registradas as decisões de revisão (inclusive as descartadas, com motivo)?**

> Resposta: `~/.config/praxisforge/`

### F. Promoção e ciclo de vida (etapa 4)

**F1. A promoção abre o PR automaticamente ou só prepara os arquivos?**

> Resposta: PR auto

**F2 ★. Quando o fork muda (`scan` volta a pasta para `in_curation`), a triagem roda só nos artefatos
cujo hash mudou?**

> Resposta: `in_curation` a triagem roda só nos artefatos atualizados

**F3. Uma skill cuja fonte mudou recebe nova versão automaticamente (proposta de bump) ou só um
alerta?**

> Resposta: só alerta

**F4. Várias fontes podem alimentar a mesma skill (ex.: TDD de dois repositórios)? Quem decide a
fusão?**

> Resposta: LLM

### G. Legado

**G1. As curadorias já feitas (`andrej_karpathy_skills`, `agent_skills`) são refeitas pelo pipeline
novo?**

> Resposta: sim, código deve ter algum recurso indeitifica se está incompleto, até para problemas no processamento.

**G2. O PR #21 é mergeado como está, ou espera a curadoria completa do `agent_skills`?**

> Resposta: merge now

---

## Análise das respostas (25/09/2026)

### 1. Decisões fechadas

| # | Decisão |
|---|---------|
| A1 | Curadoria cobre **todos** os tipos: skills, references, commands, agents, hooks e rules |
| A2 | Tudo que o praxisforge produz fica **no repositório** (Princípio VI / ADR 0009) |
| A4 | Base de conhecimento **agnóstica**: nada é descartado por tema; tudo é curado |
| B1 | Manifesto do inventário fora do repo, junto do registro (`~/.config/praxisforge/`) |
| C1 | Triagem via `claude` CLI |
| C2 | Dois modelos: um mais barato para a triagem, outro para o rascunho |
| C4 | Um prompt por artefato |
| C6 | Prompts de curadoria versionados no repo; fazem parte do processo |
| D1 | Só se extraem **ideias**: nada literal e nada derivado |
| D2 | Fontes `link`/`unknown`: o LLM recebe só o resumo das ideias |
| D3 | Teste de similaridade será implementado |
| E1 | Staging em `curation/<alias>/` |
| E2 | Revisão por comando da CLI |
| E3 | Só vereditos "lacuna" exigem aprovação |
| E4 | Decisões de revisão em `~/.config/praxisforge/` |
| F1 | Promoção abre o PR automaticamente |
| F2 | Pasta em `in_curation`: triagem só dos artefatos alterados |
| F3 | Fonte alterada: só alerta, sem bump automático |
| G1 | Curadorias antigas são refeitas; o processo detecta curadoria incompleta ou interrompida |
| G2 | PR #21 é mergeado agora |

### 2. Conflitos entre respostas (precisam de decisão)

**K1. D4 × feature 008 × constituição.** "Nada no escopo global" contradiz o
`skills publish --target global` já implementado e o Princípio VI, que prevê publicação "em outros
projetos". Três leituras possíveis:
(a) remover só o alvo `global` e manter a publicação em pastas de projeto;
(b) remover toda publicação, e o repo passa a ser só acervo;
(c) manter o código e só não usar.
→ Recomendação: **(a)**. Exige ADR e emenda da constituição.

> Resposta: a

**K2. A3 × D1.** Guardar "o conteúdo" do `CLAUDE.md`/`AGENTS.md` de terceiros num README contradiz
"só ideias": seria cópia.
→ Recomendação: o índice guarda a **síntese das ideias** de cada arquivo, com link para a
origem, e não o texto.

> Resposta: recomendação

**K3. F4 × E3.** Se o LLM decide a fusão de fontes e só "lacuna" pede aprovação, uma fusão alteraria
um item já aprovado sem ninguém ver.
→ Recomendação: o LLM **propõe** a fusão, e toda fusão entra na revisão como "lacuna".

> Resposta: recomendação

**K4. C1 × segurança.** Com o CLI, a chamada precisa rodar **sem ferramentas** (nada de Bash/Write),
e só o código grava arquivos. A proteção contra prompt injection depende disso.
→ Confirmar como requisito não negociável.

> Resposta: confirmo

**K5. D1 × G2.** A `guarda-barra-qualidade` é **derivada** (tradução adaptada). Com D1 = "só
ideias", ela não cabe na regra nova.
→ Recomendação: merge agora (a licença MIT permite, e o aviso já foi adicionado) e marcá-la para
reescrita na refação do G1.

> Resposta: recomendação

### 3. Respostas que precisam de esclarecimento

**B2.** A resposta descreve uma estrutura de pastas, e não o método de classificação. Proposta que
une as duas coisas:
- **Classificação:** por convenção de caminho (`skills/*/SKILL.md`, `.claude/commands/*.md`,
  `agents/*.md`, `hooks/*`, `.claude/rules/*.md`, `references/*.md`). O que não casar vai para o
  tipo `unknown` e segue para a revisão, nunca é descartado em silêncio.
- **Estrutura no repo:** ver a proposta P1 abaixo.

> Resposta: sim

**B3.** "Sim" para as três opções. Proposta de combinação:
1. lista fixa: `.git/`, `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, `graphify-out/`;
2. mais o `.gitignore` da própria pasta;
3. mais o limite de tamanho (256 KB) e a detecção de binário (byte nulo).

Todo item ignorado entra no manifesto como `ignored` com o motivo, e não some.

> Resposta: manifesto.

### 4. Propostas pedidas

**P1. Estrutura no repositório (B2, D4, A2).** O nome `skills/` fica pequeno para seis tipos.
Proposta: `library/`.

```
library/
├── INDEX.md                  # índice geral (A3): um item por linha, com tipo, fonte e ideia central
├── skills/<nome>/SKILL.md    # + arquivos de apoio
├── commands/<nome>.md
├── agents/<nome>.md
├── hooks/<nome>/             # script + README explicando o evento e o uso
├── rules/<nome>.md
├── references/<nome>.md      # checklists e guias usados por outros itens
└── _templates/               # um template por tipo
curation/<alias>/             # staging (E1): propostas aguardando revisão
prompts/curation/             # prompts versionados (C6): triage.md, draft.md, merge.md
```

- `skills/` atual migra para `library/skills/` (breaking: ADR + ajuste do `skills validate/catalog/publish`).
- Cada item mantém `metadata.sources` e a versão; o validador passa a ser por tipo.

> Resposta: aprovado.

**P2. Contexto de comparação sem o CLAUDE.md global (C3).** Tudo dentro do repo:
- `library/INDEX.md`, com nome e ideia central de cada item já no acervo;
- o conteúdo completo dos 3 itens **do mesmo tipo** mais parecidos com o artefato (escolhidos por
  palavras-chave do nome e da descrição, sem LLM);
- `prompts/curation/criteria.md`: critérios versionados do que é "coberto", "lacuna" e "fora de
  escopo".

O veredito passa a significar "já existe no acervo", e não "já está nas regras pessoais".

> Resposta: aprovado.

**P3. Teto de custo e retomada (C5, G1).**
- Estado por pasta em `~/.config/praxisforge/curation/<alias>/state.json`: para cada artefato do
  manifesto, hash, etapa (`pending`, `triaged`, `drafted`, `reviewed`, `promoted`, `failed`,
  `ignored`), veredito, custo e tentativas.
- Teto por execução, com dois limites configuráveis: número de chamadas e valor em US$ (lido da
  saída JSON do CLI quando ela informar o custo; senão, conta só as chamadas).
- Ao atingir o teto: termina o artefato em curso, grava o estado, sai com código próprio
  (ex.: 4) e mostra o comando de retomada (`praxisforge curation run <alias> --resume`).
- **Curadoria completa** = todo artefato do manifesto em estado terminal (`promoted`, `ignored`,
  ou veredito aceito). Qualquer outro estado marca a pasta como incompleta. Isso atende o G1,
  inclusive falhas no meio do processamento.
- Falha num artefato vira `failed` com o motivo, e o lote continua (graceful degradation).

> Resposta: aprovado.

**P4. Similaridade (D3).** A saída é em pt-BR e a fonte quase sempre em inglês, então a comparação
por palavras não detecta tradução. Proposta em duas camadas:
1. **Estrutural (código):** compara a sequência de títulos, o número de itens de lista e de tabelas
   e a ordem dos passos. Sobreposição de estrutura ≥ 0,7 → sinaliza.
2. **Juiz (LLM barato, sem ferramentas):** recebe original e proposta e responde, com schema,
   "é tradução ou paráfrase próxima?" com justificativa.

Proposta sinalizada por qualquer camada é regenerada uma vez com instrução de reescrever pelas
ideias. Se continuar sinalizada, vai para a revisão como "lacuna" com o alerta. O limiar 0,7 é o
ponto de partida, calibrado com os casos reais (a `guarda-barra-qualidade` deve ser sinalizada).

> Resposta: aprovado.

### 5. Impacto (para a spec)

- **Constituição:** emendas no Princípio VI (acervo `library/`, alcance da publicação) e na política
  de extração (só ideias).
- **ADRs novos:** estrutura `library/`, pipeline de curadoria, extração só de ideias.
- **Schema:** `source-schema` v3 (breaking). O `extract_policy` deixa de ter níveis; a licença
  passa a ser só registro.
- **Tamanho:** isto é maior do que uma feature. Sugestão de divisão:
  1. `library/` + validadores por tipo + migração de `skills/`;
  2. inventário + estado + retomada (sem LLM);
  3. triagem, rascunho e similaridade via CLI;
  4. revisão (CLI) + promoção com PR automático.

---

## Resultado do debate (25/09/2026)

Todas as questões respondidas. K1 = (a): remover só o alvo `global`, mantendo a publicação em pastas
de projeto. K2–K5 e P1–P4 aceitos como recomendados. B2 = classificação por convenção de caminho,
com fallback `unknown` para revisão. B3 = lista fixa + `.gitignore` + tamanho/binário, com cada
item ignorado registrado no manifesto.

### Divisão em 4 features (ordem de dependência)

| # | Feature | Escopo | Depende de |
|---|---------|--------|------------|
| 009 | `009-acervo-library` | `library/` com um diretório por tipo + `INDEX.md` + `_templates/`; validadores por tipo; migração de `skills/`; remoção do alvo `global` (K1); `source-schema` v3 só ideias (D1); emendas da constituição + ADRs | — |
| 010 | `010-inventario-curadoria` | inventário determinístico (B2/B3), manifesto e `state.json` em `~/.config/praxisforge/curation/<alias>/`, detecção de curadoria incompleta (G1), triagem incremental por hash (F2); sem LLM | 009 |
| 011 | `011-triagem-llm` | `claude` CLI sem ferramentas (K4), dois modelos (C2), um prompt por artefato (C4), contexto do acervo (P2), prompts versionados em `prompts/curation/` (C6), teto de custo + `--resume` (P3), similaridade em duas camadas (P4), staging em `curation/<alias>/` | 010 |
| 012 | `012-revisao-promocao` | `praxisforge curation review` (E2), aprovação só de "lacuna" e fusões (E3/K3), decisões em `~/.config/praxisforge/` (E4), promoção para `library/` + validação + PR automático (F1), alerta de fonte alterada (F3), refação das curadorias legadas (G1/K5) | 011 |

Próximo passo: `/speckit-specify` da 009.
