# objetivo-init — PraxisForge

> **RASCUNHO — gerado a partir de `objetivo-init-minimal.yaml` + contexto da conversa, revisado em 18/09/2026.**
> Campos marcados `⚠️ SUPOSIÇÃO` foram inferidos (do histórico da conversa e do perfil salvo do usuário) e precisam de confirmação.
>
> _meta: criado_em: "18/09/2026 15:59" | modificado_em: "18/09/2026 17:40"

---

## description

> PraxisForge — Curadoria e engenharia de agentes para Claude: pesquisa, síntese e refino contínuo de conhecimento aplicado ao desenvolvimento de agentic AI.

---

## specification

- **project_name**: `PraxisForge`
- **created_at**: `18/09/2026`
- **modify_at**: `18/09/2026`
- **owner**: Yves Marinho
- **description**: Projeto de curadoria e engenharia de agentes e agenticas para Claude, com objetivo de aprimorar a tecnologia dos agentes através de múltiplas fontes de conhecimento.
- **output_format**: Skills (pasta `skills/<nome>/` com `SKILL.md` + arquivos de apoio), definições de agentes (arquivos `.md` e demais arquivos do agent: scripts, templates, referências), artefatos, códigos e documentos de curadoria/pesquisa (Markdown) e templates/padrões de agentes reutilizáveis
- **docstring_style**: `reStructuredText` (com doctest) — conforme preferência salva do usuário
- **primary_workflow**: `pesquisa de fontes → curadoria/avaliação → registro de proveniência → síntese → produção de skill/agente/documento → validação → publicação`
- **planning_workflow**: `objetivo-init-praxisforge.md → architecture debate → project constitution → specification → plan → tasks → implementation`
- **scope_boundary**: Itens fora do escopo documentados separadamente em `docs/out-of-scope.md`

### objetivos

1.  Curar e consolidar fontes de conhecimento (papers, documentação oficial, comunidades, repositórios) sobre engenharia de agentes e agentic AI aplicada ao Claude
2.  Desenvolver e manter uma biblioteca de skills, padrões e templates de agentes reutilizáveis, versionados e documentados
3.  Estabelecer e documentar boas práticas de engenharia de agentes (arquitetura, prompts, avaliação, observabilidade) para uso contínuo em projetos futuros

---

### architecture

**statement**: Adotar arquitetura em camadas com Application, Domain e Infrastructure, seguindo DDD leve, SOLID, validação de contratos, testes automatizados e observabilidade por logs estruturados.

- **style**: Camadas + Casos de Uso; portas/adapters apenas onde há integração externa (pastas de origem, IA, filesystem)
- **layers**:
  - Presentation — CLI; sem regra de negócio
  - Application — casos de uso (varrer, curar, sintetizar, validar, publicar), orquestração, DTOs
  - Domain — entidades (Fonte, Skill, PastaOrigem, Proveniência), regras de negócio, contratos, value objects
  - Infrastructure — I/O, filesystem, leitura/escrita de `src/data` (repositório YAML), integrações externas, adapters (inclui providers de IA)
- **principles**:
  - DDD leve — apenas para modelar domínio e linguagem ubíqua
  - SOLID como critério de revisão, não como obsessão
  - TDD para partes críticas do domínio
  - GoF apenas quando houver problema real que justifique (Strategy, Factory, Adapter, Facade, Builder)
  - Contratos de entrada/saída com schemas versionados e validação explícita
  - Logs estruturados para observabilidade, aplicados apenas nas bordas (Application/Infrastructure)
  - Configuração por arquivos e variáveis de ambiente

**mandatory_requirements**:
- Testes unitários + integração + CLI
- Lint, typing e coverage obrigatórios no CI
- Toda entrada validada antes de chegar ao domínio
- Integrações externas encapsuladas na camada Infrastructure
- Camada Domain sem dependência de framework, CLI, logger concreto ou SDK externo
- Domain/Application levantam exceções tipadas e nomeadas; nunca retornam `False` como substituto genérico de erro
- Infrastructure e CLI/presentation capturam exceções **específicas** (nunca `BaseException`; `except Exception` apenas como último recurso no `main()`) com `try/except` nas fronteiras, registram via `logging.error` a descrição do erro + `exc_info=True` + a exceção capturada, e retornam `False`
- Domain layer não contém chamadas a logging; apenas Application/Infrastructure registram logs
- Toda integração de IA implementa uma interface Strategy/Adapter comum; nenhum provider é fixado no framework mínimo
- Toda saída estruturada relevante é versionada por SemVer (`schemas/<dominio>-schema-v<major>.json`) e carrega campo obrigatório `schema_version`


**error_handling_standard**:
- Domain e Application levantam exceções tipadas; nunca retornam `False` como substituto genérico de erro
- Infrastructure e CLI/presentation capturam exceções **específicas** (nunca `BaseException`; `except Exception` apenas como último recurso no `main()`) com `try/except` nas fronteiras, registram via `logging.error` a descrição do erro + `exc_info=True` + a exceção capturada, e retornam `False`
- Falhas recuperáveis são registradas em log e propagadas de forma controlada; falhas não recuperáveis abortam a operação atual com mensagem clara
- Processamentos em lote registram falhas por item sem interromper o lote inteiro, quando aplicável

**ai_integration_standard**:
- Nenhum provider de IA é fixado no framework mínimo; toda integração implementa uma interface Strategy/Adapter comum (ex.: `SummaryProvider`, `AIClientPort`)
- Credenciais de IA seguem o padrão global de `.secrets/`, nunca hardcoded ou expostas em comandos CLI

**key_dependencies**:
- `pyyaml` (registros YAML), `pydantic` (contratos/DTOs), `jsonschema` (validação de schemas), `requests` (HTTP)
- Qualidade: `pytest`, `ruff`, `mypy`
- IA: interface Strategy/Adapter comum; SDK Anthropic como primeiro adapter (não fixado no núcleo)

**schema_versioning**:
- pattern: `schemas/<dominio>-schema-v<major>.json`
- required_field: `schema_version` em toda saída estruturada (JSON, YAML ou frontmatter Markdown); o JSON Schema correspondente valida todos os formatos
- rule: Mudança breaking de contrato = novo arquivo com major version incrementado; mudanças aditivas/compatíveis não exigem novo arquivo

---

### regras_projeto

-  ✅ Toda fonte de conhecimento curada deve ter proveniência registrada (origem, data, licença/direitos)
-  ✅ Priorizar Markdown estruturado e YAML para curadoria de conhecimento (fontes, skills, ADRs)

- ✅ Use Python (3.12+) como linguagem principal de automação; shell apenas para orquestração simples
- ✅ Use `uv` como gerenciador de ambiente Python
- ✅ Toda requisição de API deve usar Python (biblioteca `requests`); nunca usar `curl` para validação
- ✅ Gerenciamento de configuração: todos os segredos/credenciais em `.secrets/` (não versionado e não mencionado no chat)
- ✅ Qualidade de código obrigatória: PEP 8, formatação `ruff format`, type hints (`mypy`), linting (`ruff`), testes (`pytest`)
- ✅ Manter projeto limpo: sem arquivos redundantes; `.gitignore` claro; versionar apenas artefatos essenciais

### regras_gerais

- 📁 Organização de arquivos: fonte em `src/`, scripts em `scripts/`, testes em `tests/`, docs em `docs/` (sem arquivos de projeto na raiz, exceto configurações essenciais)
- 🔐 Segurança: usar `.secrets/` para todas as credenciais; arquivos `.env` nunca commitados; `bandit` + `safety` checks em CI/pre-commit
- 📝 Documentação: todo bloco de código deve ter docstrings (reST + doctest); ADRs em formato MADR simplificado (Contexto, Decisão, Consequências, Alternativas) para decisões arquiteturais em `docs/decisions/`; visão geral (camadas, fluxo, decisões) em `docs/architecture/overview.md`; READMEs para cada módulo principal
- 📦 Controle de versão: commits atômicos com mensagens detalhadas; branches de feature seguem convenção de nomenclatura; sem commits sem testes passando
- 🔄 Gerenciamento de branches: nunca commitar direto na branch principal (`main`); trabalhar em branch de feature e integrar via pull request após conclusão do objetivo; limpar branches mescladas. Branch principal confirmada: `main` (repo migrado de `master` em 18/09/2026, scaffold rebaseado sobre o `origin/main`; push ainda pendente)
- 🧪 Ordem TDD (features com regra de negócio): contrato/DTO → exceções semânticas → testes de falha (vermelho) → implementação (verde) → refatoração
- 🪝 Pre-commit obrigatório: lint + tipagem + GitGuardian (`ggshield secret scan pre-commit`), configurado para execução manual; commit bloqueado por secret = remover o secret e refazer, nunca `--no-verify`
- ✅ Quality gates bloqueantes no CI: `ruff check .` → `mypy` (0 erros) → `pytest --cov-fail-under=90`; falha em qualquer etapa impede o merge
- 📋 Validação de configuração: `yamllint` para todos os arquivos YAML; `check-jsonschema` para validação de JSON
- 🧪 Estratégia de testes: `pytest` para testes unitários/integração; nunca curl manual (sempre Python `requests`)
- 🚀 Prontidão para deploy: scripts devem ser idempotentes; configuração do ambiente reproduzível do zero; tratamento de erros abrangente
- 🐛 Rastreamento de bugs: todo erro/problema deve gerar bug-report em `docs/bugs/` com timestamp, stack trace, passos de reprodução e workaround
- 📊 Rastreamento de sessão: todo trabalho registrado no vault Obsidian `claude_memory`, na pasta `daily/` (nota `daily/YYYY-MM-DD.md`), com timestamps, decisões e resultados
- 🧠 Memória/documentação via Obsidian: todas as informações persistentes do projeto usam o vault Obsidian `claude_memory` — dados de sessão em `daily/`, dados do projeto em `projects/` (nota `projects/praxisforge.md`); toda nota criada deve ser listada, com descrição, no `00-index.md` do vault
- 🔐 Antes de gravar no vault: sem tokens/senhas, IPs internos ou endpoints com credenciais

---

## folder_structure

- `.github` — Workflows e ações para CI/CD (gerados automaticamente)
- `.git-hooks` — Hooks personalizados para Git (gerados automaticamente)
- `.secrets` — Armazenamento seguro de chaves e tokens (não versionado)
- `.specify` — Configurações específicas do projeto (geradas automaticamente)
- `.editor` — Configurações de IDE/editor e integrações de agentes de IA (geradas automaticamente, agnóstico de ferramenta/editor específico)
- `src/data` — Dados versionados do projeto: `src/data/folders.yaml` (registro das pastas a curar) e `src/data/sources/` (registro curado de fontes)
- `src/data/sources` — Registro curado e versionado de fontes de conhecimento (`src/data/sources/<categoria>/<slug>.md`, um arquivo por fonte, frontmatter YAML com proveniência: origem, data, licença/direitos, relevância; notas de leitura e extratos). Material bruto **não** é versionado: fica na pasta externa `~/DevOps/github_forks` (forks/repositórios de origem), referenciada por `alias` em `src/data/folders.yaml`, com o caminho real resolvido por config/variável de ambiente (ex.: `PRAXISFORGE_FOLDER_GITHUB_FORKS`), nunca caminho absoluto no YAML nem no código. Licença validada **por fonte**: campo `license` obrigatório no frontmatter; fonte sem licença registrada fica com status "pendente" e não gera extrato copiado para o repo
- `skills` — Biblioteca de skills produzidas/refinadas pelo projeto (`skills/<nome>/SKILL.md`). **Fonte de verdade versionada em git** (histórico, PR, CI, lint dos `SKILL.md`); o vault `claude_memory` **não** guarda cópia das skills — só catálogo em `projects/praxisforge.md` e templates/guias de criação de skill em `skills/`
- `scripts/publish-skills` — Publica skills do repo em `~/.claude/skills/` (global) ou `.claude/skills/` de outro projeto, via cópia/symlink idempotente (ex.: `make publish-skills`)
- `docs` — Documentação geral do projeto
- `docs/architecture` — Documentos de arquitetura e design
- `docs/architecture/overview.md` — Visão geral da arquitetura (camadas, fluxo, decisões)
- `docs/decisions` — Architecture Decision Records (MADR simplificado)
- `docs/out-of-scope.md` — Itens fora do escopo do projeto
- `docs/bugs` — Repositório de bug reports (obrigatório para cada erro encontrado)
- `docs/debates` — Documentação de debates técnicos
- `docs/guides` — Guias de como fazer tarefas comuns e boas práticas
- `docs/reference` — Documentação de referência (fluxos de sessão, integrações)
- `schemas` — Contratos JSON de saída versionados por SemVer (`schemas/<dominio>-schema-v<major>.json`), com campo `schema_version` obrigatório
- `scripts` — Scripts de automação
- `src` — Código-fonte do projeto (estrutura específica por tipo)
- `tests` — Testes automatizados (pytest)
- `tmp` — Arquivos temporários e logs (não versionados)
- `pyproject.toml` — Metadados do projeto Python, dependências, configurações (ruff, mypy)
- `Makefile` — Targets convenientes (`make setup`, `make test`, `make dev`, `make format`)
- `.gitignore` — Excluir `.secrets/`, `tmp/`, `*.pyc`, `.venv/`, `__pycache__/`

---

## expected_outcome

**primary_deliverables**:
1. Biblioteca versionada de skills e templates de agentes prontos para uso com Claude
2. Repositório curado e documentado de fontes de conhecimento sobre engenharia de agentes (com proveniência e avaliação de qualidade)
3. Guia de padrões e boas práticas de engenharia de agentes (arquitetura, prompts, avaliação) consolidado em `docs/guides/`

**success_criteria**:
- Pelo menos 95% das skills/agentes publicados documentados e validados (lint do `SKILL.md`, arquivos de apoio presentes, proveniência das fontes de origem registrada) por ciclo de curadoria; ciclo mensal, com revisão registrada em `daily/` no vault
- Cada fonte curada possui registro de proveniência e critério de relevância aplicado
- Todos os testes passando (`pytest --cov` mostra 90%+ de cobertura, gate bloqueante no CI)
- Verificação de segurança limpa (sem credenciais no repo, relatório `bandit`/`safety` verde)
- Documentação completa (README, ADRs em MADR simplificado, guias)
- Reproduzível do zero: clone limpo → executar script de setup → ambiente completo funcionando

**quality_gates**:
- Código: 100% type hints (`mypy` strict, gate bloqueante no CI, 0 erros), 0 violações `ruff`, formatado com `ruff format`
- Testes: 90%+ cobertura (branches, `--cov-fail-under=90`), todos os testes em menos de 5s, sem testes instáveis
- Segurança: sem segredos hardcoded, todas as entradas validadas, tratamento de erros adequado (exceções tipadas em domain/application; try/except + False nas fronteiras de infrastructure/CLI)
- Documentação: toda função tem docstring (reST + doctest), toda decisão de design registrada em ADR (MADR simplificado)

---

## ai_safety_instructions

**REGRAS CRÍTICAS — Devem ser rigorosamente seguidas por assistentes de IA sem exceção**

**security_and_privacy**:
- 🚨 NUNCA expor, mencionar ou ecoar dados sensíveis no chat: senhas, chaves de API, tokens, credenciais, nomes de usuário, endereços de email, endereços IP, URLs privadas, chaves SSH, credenciais de banco, ou qualquer PII
- 🚨 NUNCA exibir caminhos completos para arquivos contendo segredos, mesmo ao mencionar a estrutura de diretórios
- 🚨 SEMPRE mascarar ou redigir dados sensíveis em logs, mensagens de erro e saídas de debugging antes de exibir
- 🚨 NUNCA armazenar histórico de sessão, logs de chat ou artefatos de trabalho em controle de versão se contiverem QUALQUER informação sensível
- 🚨 Se um usuário colar dados sensíveis acidentalmente, sinalizar imediatamente e solicitar o uso de valores placeholder

**code_and_artifact_handling**:
- ✅ APENAS criar arquivos explicitamente solicitados pelo usuário ou essenciais para completar a tarefa
- ✅ NUNCA gerar arquivos além do que está especificado na solicitação do usuário — **exceção**: notas do vault Obsidian `claude_memory` (`daily/`, `projects/`) e a atualização do `00-index.md`, exigidas pelas regras de memória/sessão
- ✅ NUNCA modificar arquivos de governança do agente de IA configurado sem consentimento explícito do usuário
- ✅ SEMPRE preservar comentários, docstrings e estilo de documentação existentes ao editar arquivos
- ✅ Ao editar arquivos YAML/JSON, manter indentação e estrutura corretas; validar sintaxe antes de commitar
- ✅ NUNCA usar comandos de terminal (`cat`, `echo`, heredoc, `mv`, `cp`, `rm`) para operações de arquivo; usar ferramentas designadas — **exceção**: `scripts/publish-skills`, que copia/cria symlinks de skills por definição

**communication_standards**:
- 📝 NUNCA assumir intenção do usuário; fazer perguntas de clarificação se a solicitação for ambígua
- 📝 SEMPRE explicar quais alterações estão sendo feitas e POR QUÊ antes de executá-las
- 📝 Manter respostas concisas e diretas; evitar preâmbulos desnecessários
- 📝 Ao descrever localizações de arquivo, SEMPRE usar links markdown adequados
- 📝 SEMPRE seguir as convenções de cabeçalho e formato das regras globais do usuário (registro de sessão vai para o vault `claude_memory`, não para o repo)

**task_execution**:
- 🎯 SEMPRE completar a solicitação completa do usuário antes de encerrar o turno
- 🎯 Usar chamadas de ferramentas paralelas (quando seguro) para reunir contexto mais rapidamente
- 🎯 NUNCA pular etapas de validação ou testes; executar testes/linters antes de declarar trabalho completo
- 🎯 Se bloqueado por contexto ausente, pesquisar/ler arquivos proativamente em vez de perguntar ao usuário
- 🎯 Ao encontrar erros, criar bug-reports em `docs/bugs/` com timestamp, stack trace, passos de reprodução, correção e workaround

**documentation_and_accuracy**:
- 📖 SEMPRE documentar premissas, trade-offs e decisões tomadas durante a implementação
- 📖 NUNCA inventar ou alucinar caminhos de arquivo, comandos ou assinaturas de API; verificar no workspace/documentação
- 📖 SEMPRE validar sintaxe YAML/JSON usando ferramentas de linting apropriadas antes de marcar como completo
- 📖 SEMPRE citar ou vincular a arquivos/linhas de origem relevantes ao explicar comportamento de código

---

## profile

- **role**: Desenvolvedor Python/Bash e administrador de sistemas Linux, atuando na curadoria e engenharia de agentes de IA
- **experience_level**: Avançado (conforme perfil salvo: usuário avançado de Linux, administra múltiplos sistemas de infraestrutura)
- **expertise_by_domain**:
  - domain: `Administração de sistemas Linux` | level: `Avançado` | focus: `Linux Mint 22, automação via Bash/Python`
  - domain: `Bancos de dados` | level: `Avançado` | focus: `MySQL, PostgreSQL, clusters com Percona`
  - domain: `Orquestração e automação` | level: `Avançado` | focus: `Docker, Kubernetes, Traefik, Ansible, Terraform, n8n, Airflow`
  - domain: `Engenharia de agentes de IA` | level: `Em desenvolvimento (foco do PraxisForge)` | focus: `Curadoria de conhecimento, skills e agentes para Claude`


- **core_objectives**: *(ver seção "objetivos" acima)*
- **constraints**:
  - Projeto individual (sem equipe/colaboradores até segunda ordem; sem RBAC/multi-tenant)
  - Sem segredos externos no código; todas as credenciais em `.secrets/` (não versionado)
- **tool_preferences**:
  - Python 3.12+ para todos os scripts e automação
  - Make/shell para orquestração simples; Python para lógica complexa
  - Pytest para testes; nunca usar curl manual (sempre usar Python `requests`)
  - Hooks pre-commit para aplicar qualidade antes dos commits
  - `docker compose` (não `docker-compose`); `docker-compose.yaml` sem o parâmetro `version`
  - VS Code como IDE principal
- **work_style**:
  - Desenvolvimento orientado por especificação (SDD): spec → plan → tasks → implement
  - Commits atômicos e bem documentados com mensagens de commit claras
  - Rastreamento de trabalho baseado em sessões (tempo, decisões, resultados no vault Obsidian `claude_memory`, pasta `daily/`)
  - Validação contínua: testes, linting e verificações de segurança em cada etapa

---

## features_to_implement

- Pipeline de curadoria de fontes de conhecimento (coleta → avaliação → registro de proveniência)
- Estrutura/template padrão para criação de novas skills validadas
- Script de publicação de skills (`scripts/publish-skills`): repo → `~/.claude/skills/` ou `.claude/skills/` de outro projeto, idempotente
- Catálogo de skills (nome, propósito, versão, caminho no repo) mantido em `projects/praxisforge.md` no vault e em `skills/README.md` no repo, gerado a partir dos `SKILL.md` na etapa de publicação
- Base de dados das pastas que contêm informações a serem curadas (ex.: `~/DevOps/github_forks` e as demais que forem adicionadas): registra caminho configurável, descrição, tipo de conteúdo, licença, data da última varredura e status de curadoria; acessada via porta/adapter na camada Infrastructure. Armazenamento em **YAML versionado no repo** (`src/data/folders.yaml`), validado por schema versionado (`schemas/folders-schema-v1.json`, com `schema_version`) e `yamllint`/`check-jsonschema`
- Processo de síntese: transformar conhecimento curado em skill/agente/documento

---

## pending_tasks

### Phase 1 — Prerequisites
- [x] definir owner, objetivos finais e formato de saída (bloqueia o restante do planejamento)
- [x] Confirmar se o projeto será individual ou colaborativo (decide se o bloco RBAC deve ser restaurado)

### Phase 2 — Core implementation
Pipeline: `pastas de origem → registro de pastas → curadoria/avaliação → proveniência → síntese → skill/agente → validação → publicação → catálogo`. Cada tarefa segue TDD (contrato → exceções semânticas → testes de falha → implementação).

- [ ] Estruturar repositório inicial (`src/` em camadas, `docs/`, `schemas/`, `src/data/`, `skills/`, `scripts/`, `tests/`) com pre-commit (lint, tipagem, GitGuardian) e CI com quality gates
- [ ] Definir schemas versionados: proveniência de fontes (`schemas/source-schema-v1.json`) e registro de pastas (`schemas/folders-schema-v1.json`)
- [ ] Implementar o registro de pastas a curar (YAML versionado, com alias de caminho resolvido por config/variável de ambiente; primeiro registro: `github_forks`)
- [ ] Implementar a coleta/varredura das pastas registradas (adapter na Infrastructure; falha por item não derruba o lote) e atualizar data da última varredura e status de curadoria
- [ ] Implementar a curadoria/avaliação: critério de relevância + registro de proveniência (origem, data, licença por fonte) em `src/data/sources/<categoria>/<slug>.md`
- [ ] Implementar a síntese: conhecimento curado → skill/agente/documento, via interface Strategy/Adapter comum de IA (nenhum provider fixado)
- [ ] Criar template/molde de skill e de agente reutilizáveis (`SKILL.md` + arquivos de apoio) e o guia de criação no vault (`skills/`)
- [ ] Implementar a validação de skills/agentes (lint do `SKILL.md`, presença de arquivos de apoio, proveniência das fontes de origem)
- [ ] Implementar `scripts/publish-skills` (repo → `~/.claude/skills/` ou `.claude/skills/` de outro projeto, idempotente)
- [ ] Gerar o catálogo de skills: `projects/praxisforge.md` no vault e `skills/README.md` no repo
- [ ] Consolidar o guia de boas práticas de engenharia de agentes em `docs/guides/`
- [ ] Configurar o registro de sessão/projeto no vault Obsidian (`daily/`, `projects/`) e atualização do `00-index.md`

### Phase 3 — Quality validation
- [ ] Executar suite completa `pytest` (requisito 90%+ cobertura, `--cov-fail-under=90`), incluindo testes de falha/indisponibilidade para toda dependência externa (pastas de origem, provider de IA, filesystem)
- [ ] Executar `ruff check .` e `mypy` como gates bloqueantes no CI (0 erros)
- [ ] Validar schemas e YAML: `check-jsonschema` (`source-schema-v1`, `folders-schema-v1`) e `yamllint` verdes
- [ ] Teste de ponta a ponta do pipeline: pasta registrada → fonte curada com proveniência → skill/agente sintetizado → validação → publicação → catálogo atualizado
- [ ] Verificar idempotência de `scripts/publish-skills` e do pipeline (segunda execução sem efeitos colaterais)
- [ ] Verificar o critério de sucesso: ≥ 95% das skills/agentes publicados aprovados na validação
- [ ] Verificação de segurança: `bandit`, `safety`, GitGuardian, sem credenciais no repo e sem dados sensíveis nas notas do vault
- [ ] Reprodutibilidade: clone limpo → setup → ambiente funcionando (sem depender de caminhos absolutos da máquina)
- [ ] Revisão final de documentação (README, ADRs em MADR simplificado, guias, vault sincronizado com `00-index.md`) e verificação de completude

---

## Resumo das decisões pendentes (revisar antes de aprovar este documento)

| # | Item | Ação necessária |
|---|------|------------------|
| — | Nenhuma decisão pendente | Revisar e aprovar este documento |
