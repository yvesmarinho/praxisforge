<!-- Criado em: 25/09/2026 14:23 -->
<!-- Modificado em: 25/09/2026 14:40 -->

# Feature Specification: Inventário de curadoria por pasta

**Feature Branch**: `010-inventario-curadoria`

**Created**: 25/09/2026

**Status**: Draft

**Input**: User description: "Feature 010 da curadoria automatizada (debate em docs/debates/curadoria-automatizada.md, 25/09/2026). Inventário determinístico, sem LLM, de cada pasta registrada: classifica cada artefato por convenção de caminho (fallback unknown), ignora arquivos gerados, grandes ou binários registrando o motivo, grava um manifesto e um estado por pasta fora do repositório (junto do registro), detecta curadoria incompleta ou interrompida e, numa pasta que voltou para in_curation, marca para nova triagem só os artefatos alterados. Fora de escopo: triagem por LLM, similaridade, revisão e promoção (features 011–012)."

## Clarifications

### Session 2026-09-25

- Q: Onde ficam as convenções de classificação? → A: `~/.config/praxisforge/curation-conventions.yaml` (junto do registro, fora do repo); o repo guarda só `src/data/curation-conventions.example.yaml`.
- Q: Arquivos ignorados e "contados, não curados" entram no estado (etapa `ignorado`) ou só no manifesto? → A: Só no manifesto; o estado guarda apenas artefatos curáveis e a etapa `ignorado` fica reservada ao descarte decidido na triagem/revisão (011/012).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inventariar uma pasta sem esquecer nada (Priority: P1)

O curador pede o inventário de uma pasta registrada. O praxisforge percorre a pasta e lista
**cada** artefato encontrado com o tipo, o caminho e uma impressão do conteúdo. Arquivos que não
interessam (gerados, grandes, binários) também aparecem, marcados como ignorados e com o motivo. O
resultado fica gravado, e nada some sem registro.

**Why this priority**: é a correção do erro que originou o debate: na curadoria manual do
`agent_skills`, commands, agents, hooks, references e o `CLAUDE.md` ficaram de fora sem ninguém
perceber. Sem um inventário completo, as features 011 e 012 herdam o mesmo buraco.

**Independent Test**: inventariar uma cópia do `agent-skills` e conferir que as 25 skills, os
commands, agents, hooks, references, rules e o `CLAUDE.md`/`AGENTS.md` aparecem, cada um com o tipo
certo; `graphify-out/` e `node_modules/` aparecem como ignorados.

**Acceptance Scenarios**:

1. **Given** uma pasta registrada com skills, commands, agents, hooks, rules e references nas
   convenções conhecidas, **When** o curador pede o inventário, **Then** cada artefato é listado com
   o tipo correspondente.
2. **Given** um `CLAUDE.md` ou `AGENTS.md` na raiz da pasta, **When** o inventário roda, **Then** ele
   é listado como instrução de projeto.
3. **Given** arquivos que não casam com nenhuma convenção, **When** o inventário roda, **Then** eles
   são tratados conforme a regra de arquivos avulsos (FR-005), nunca descartados em silêncio.
4. **Given** `node_modules/`, `graphify-out/`, um binário e um arquivo acima do limite de tamanho,
   **When** o inventário roda, **Then** cada um aparece como ignorado com o motivo.
5. **Given** o mesmo inventário rodado duas vezes sem mudança na pasta, **When** o segundo termina,
   **Then** o manifesto é idêntico ao primeiro.

---

### User Story 2 - Saber se a curadoria de uma pasta está completa (Priority: P1)

O curador quer saber, para uma pasta ou para todas, quantos artefatos estão em cada etapa e se a
curadoria terminou. Uma curadoria interrompida no meio (por teto de custo, falha ou abandono) tem de
aparecer como incompleta, com o que falta.

**Why this priority**: a decisão G1 exige detectar curadorias incompletas, inclusive as antigas
(`andrej_karpathy_skills`, `agent_skills`), que serão refeitas. Sem esse estado, a 011 não tem como
retomar de onde parou.

**Independent Test**: inventariar uma pasta e consultar o status: "incompleta, N pendentes". Marcar
à mão todos os artefatos como finalizados no estado e consultar de novo: "completa".

**Acceptance Scenarios**:

1. **Given** uma pasta recém-inventariada, **When** o curador consulta o status, **Then** vê o total
   por etapa e a indicação "incompleta" com o número de artefatos pendentes.
2. **Given** uma pasta em que todos os artefatos chegaram a uma etapa final, **When** o curador
   consulta o status, **Then** ela aparece como "completa".
3. **Given** uma pasta registrada como `curated` mas sem inventário, **When** o curador consulta o
   status geral, **Then** ela aparece como "sem inventário" (curadoria legada a refazer).
4. **Given** uma pasta com artefatos que falharam, **When** o curador consulta o status, **Then** as
   falhas aparecem com o motivo e a pasta é "incompleta".

---

### User Story 3 - Refazer só o que mudou (Priority: P2)

Quando um fork recebe commits novos, a varredura já devolve a pasta para `in_curation`. Ao
inventariar de novo, só os artefatos novos ou alterados voltam a ficar pendentes; os que não
mudaram mantêm a etapa em que estavam; os que sumiram são marcados como removidos.

**Why this priority**: evita refazer a curadoria inteira (e pagar de novo a triagem da 011) a cada
atualização do fork (decisão F2).

**Independent Test**: inventariar, marcar tudo como finalizado, alterar um arquivo e remover outro
na pasta, inventariar de novo: só o alterado fica pendente, o removido aparece como removido e o
resto mantém a etapa.

**Acceptance Scenarios**:

1. **Given** um artefato finalizado cujo conteúdo mudou, **When** o inventário roda de novo, **Then**
   ele volta para pendente.
2. **Given** um artefato finalizado sem mudança, **When** o inventário roda de novo, **Then** ele
   continua finalizado.
3. **Given** um artefato que deixou de existir na pasta, **When** o inventário roda de novo, **Then**
   ele é marcado como removido (não apagado do estado).
4. **Given** um artefato novo, **When** o inventário roda de novo, **Then** ele entra como pendente.

---

### User Story 4 - Inventariar todas as pastas de uma vez (Priority: P3)

O curador pede o inventário de todas as pastas registradas. Uma pasta inacessível ou com problema
não impede as outras; o resumo final diz quantas foram inventariadas e quais falharam.

**Why this priority**: são 55 pastas registradas; conveniência e robustez de lote.

**Independent Test**: registrar três pastas, tornar uma inacessível, inventariar todas: duas
inventariadas, uma falha com motivo, código de saída de falha.

**Acceptance Scenarios**:

1. **Given** pastas registradas acessíveis e uma inacessível, **When** o curador inventaria todas,
   **Then** as acessíveis são inventariadas e a inacessível aparece como falha com o motivo.
2. **Given** pastas com status `ignore`, **When** o curador inventaria todas, **Then** elas são
   puladas.

---

### Edge Cases

- Pasta registrada cujo caminho não existe mais: falha daquela pasta, sem alterar o estado anterior.
- Link simbólico dentro da pasta apontando para fora dela: não é seguido; aparece como ignorado.
- Link simbólico em ciclo: não trava o inventário.
- Arquivo ilegível (permissão): aparece como ignorado com o motivo, e o inventário continua.
- Pasta sem nenhum artefato reconhecível: inventário válido com zero artefatos de tipo conhecido.
- Skill com arquivos de apoio: a pasta inteira da skill é **um** artefato (o hash cobre os arquivos
  de apoio); os arquivos de apoio não viram artefatos separados.
- `.gitignore` da pasta com padrões de negação (`!arquivo`): respeitados.
- Estado anterior corrompido ou em formato desconhecido: o inventário recusa, explica e não
  sobrescreve.
- Duas execuções simultâneas sobre a mesma pasta: a segunda recusa, sem corromper o estado.
- Pasta com status `pending` (licença desconhecida): pode ser inventariada; o estado registra a
  licença como desconhecida (a extração continua valendo só para ideias).

## Requirements *(mandatory)*

### Functional Requirements

**Inventário**

- **FR-001**: O curador MUST poder inventariar uma pasta registrada (por alias) ou todas as pastas
  registradas, exceto as de status `ignore`.
- **FR-002**: O inventário MUST percorrer a pasta inteira e produzir um manifesto com cada artefato:
  tipo, caminho relativo à pasta, tamanho e impressão (hash) do conteúdo.
- **FR-003**: A classificação MUST ser por convenção de caminho, cobrindo ao menos: skills
  (`skills/*/SKILL.md` e `.claude/skills/*/SKILL.md`, a pasta inteira como artefato), commands
  (`commands/*` e `.claude/commands/*`), agents (`agents/*.md` e `.claude/agents/*.md`), hooks
  (`hooks/` e `.claude/hooks/`), rules (`rules/*.md` e `.claude/rules/*.md`), references
  (`references/*.md`) e instruções de projeto (`CLAUDE.md` e `AGENTS.md` em qualquer nível).
- **FR-004**: A lista de convenções MUST ficar fora do repositório, junto do registro de pastas
  (`~/.config/praxisforge/curation-conventions.yaml` no local padrão), e ser ampliável sem mudar
  código. O repositório mantém só um exemplo validado no CI; sem o arquivo, o inventário recusa e
  explica como criá-lo a partir do exemplo.
- **FR-005**: Arquivos de texto que não casam com nenhuma convenção MUST ser tratados assim:
  cada arquivo `.md` avulso (README, `docs/`, CONTRIBUTING…) vira um artefato `unknown` individual
  para triagem; os demais (código, configuração, scripts) NÃO viram artefatos e ficam no manifesto
  como "contados, não curados", cada um com o motivo — nada some sem registro.
- **FR-006**: MUST ser ignorado, com o motivo registrado no manifesto: (a) diretórios de uma lista
  fixa (`.git/`, `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/`, `graphify-out/`);
  (b) o que o `.gitignore` da própria pasta ignora; (c) arquivos acima de 256 KB; (d) binários;
  (e) links simbólicos que apontam para fora da pasta; (f) arquivos ilegíveis.
- **FR-007**: O inventário MUST ser determinístico: mesma pasta, mesmo manifesto (ordem estável,
  sem data no conteúdo comparável).
- **FR-008**: O inventário MUST ler a pasta sem nunca escrever nela.

**Manifesto e estado**

- **FR-009**: Manifesto e estado MUST ficar fora do repositório, junto do registro de pastas (um
  por alias), e nenhum caminho absoluto de pasta MUST entrar no repositório.
- **FR-010**: O estado MUST conter só artefatos curáveis (arquivos ignorados e "contados, não
  curados" ficam apenas no manifesto) e guardar, por artefato: hash, etapa, veredito (vazio nesta feature),
  motivo da última falha e número de tentativas.
- **FR-011**: As etapas MUST ser: pendente, triado, rascunhado, revisado, promovido, falhou,
  ignorado e removido. Nesta feature só são atribuídas pendente e removido (`ignorado` é o descarte decidido na
  triagem/revisão, não a exclusão do FR-006); as demais são
  definidas para as features 011 e 012.
- **FR-012**: Manifesto e estado MUST ter contrato versionado e ser validados ao ler e ao gravar.
- **FR-013**: A gravação MUST ser atômica; um estado anterior corrompido ou de versão desconhecida
  MUST ser recusado sem ser sobrescrito.
- **FR-014**: Duas execuções simultâneas sobre o mesmo alias MUST ser impedidas (a segunda recusa).

**Incremental**

- **FR-015**: Ao inventariar de novo, artefato novo MUST entrar como pendente; alterado (hash
  diferente) MUST voltar para pendente; inalterado MUST manter a etapa; sumido MUST virar removido.
- **FR-016**: A mudança de convenções (FR-004) MUST ser tratada como mudança: artefatos
  reclassificados voltam para pendente.

**Status**

- **FR-017**: O curador MUST poder consultar o status de uma pasta ou de todas: total por etapa e a
  situação — completa, incompleta ou sem inventário.
- **FR-018**: Uma pasta MUST ser "completa" só quando todo artefato estiver em etapa final
  (promovido, ignorado, removido ou com veredito aceito); qualquer outro caso é "incompleta".
- **FR-019**: Pastas registradas como `curated` sem inventário MUST aparecer como "sem inventário"
  (curadoria legada a refazer).

**Lote e erros**

- **FR-020**: No inventário de todas as pastas, a falha de uma MUST NOT impedir as outras; o resumo
  MUST listar as falhas com o motivo.
- **FR-021**: Códigos de saída MUST seguir o padrão da CLI (0 ok, 1 falha de validação/negócio,
  2 uso, 3 ambiente).

### Key Entities

- **Artefato**: unidade de curadoria encontrada numa pasta. Atributos: tipo (skill, command, agent,
  hook, rule, reference, instrução de projeto, unknown), caminho relativo, tamanho, hash.
- **Artefato ignorado**: arquivo ou diretório fora da curadoria, com o motivo.
- **Manifesto**: resultado do inventário de uma pasta: artefatos, ignorados, versão das convenções.
- **Estado da curadoria**: por artefato, etapa, veredito, falha e tentativas; por pasta, a situação
  (completa, incompleta, sem inventário).
- **Convenções de classificação**: tabela de padrões de caminho → tipo, no diretório do registro.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No inventário do `agent-skills`, 100% dos commands, agents, hooks, rules, references e
  instruções de projeto aparecem com o tipo correto (hoje, 0% deles entrou na curadoria manual).
- **SC-002**: Nenhum arquivo da pasta fica fora do manifesto: cada um é artefato, parte de um
  artefato ou ignorado com motivo.
- **SC-003**: Reinventariar uma pasta sem mudanças produz manifesto idêntico em 100% das execuções.
- **SC-004**: Após alterar 1 arquivo numa pasta finalizada, só 1 artefato volta para pendente.
- **SC-005**: Inventariar uma pasta com 5.000 arquivos leva menos de 10 segundos.
- **SC-006**: Nenhum byte é escrito dentro das pastas inventariadas nem no repositório.

## Assumptions

- As convenções iniciais vêm dos repositórios já registrados (ex.: `agent-skills`); pastas com
  estruturas diferentes caem no tratamento de avulsos até a lista ser ampliada.
- Um diretório `hooks/` (com `hooks.json` e scripts) é **um** artefato de hook.
- O limite de 256 KB e a lista fixa de ignorados vêm do debate (B3) e podem ser ajustados depois.
- Licença desconhecida não bloqueia o inventário: ler e classificar não extrai conteúdo.
- O estado é pensado para a triagem da 011 (teto de custo, `--resume`) e a revisão da 012, que
  atribuem as demais etapas.
- Triagem por LLM, similaridade, staging em `curation/<alias>/`, revisão e promoção ficam para as
  features 011 e 012.
