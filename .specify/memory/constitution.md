<!--
Sync Impact Report
- Version change: 3.0.0 → 4.0.0 (MAJOR: redefinição incompatível do Princípio VI — o acervo deixa
  de ser só skills/ e passa a library/ com seis tipos, e a publicação no escopo global é removida;
  Princípio V passa a admitir só a extração de ideias das fontes)
- Princípios modificados: V. Proveniência, Licença e Localização das Fontes (só ideias; licença
  obrigatória e informativa); VI. Skills Versionadas no Repositório → VI. Acervo Versionado no
  Repositório
- Seções adicionadas: nenhuma
- Seções removidas: nenhuma
- Templates: plan/spec/tasks-template leem a constituição em tempo de execução — sem alteração
- Plano de migração: feature 009-acervo-library (git mv skills/ → library/skills/, validadores por
  tipo, library/INDEX.md, publicação só em pastas de projeto, source-schema-v3 e conversão manual
  dos registros de fonte, guarda-barra-qualidade marcada para reescrita)
- TODOs adiados: revisar a "política máxima" exibida por folders show/list (feature 006)
- Motivo: debate docs/debates/curadoria-automatizada.md (25/09/2026) — curadoria de todos os tipos
  de recurso, base de conhecimento agnóstica, só ideias, nada no escopo global. ADRs 0011 e 0012
-->
<!-- Criado em: 18/09/2026 17:50 -->
<!-- Modificado em: 25/09/2026 12:40 -->

# PraxisForge Constitution

## Core Principles

### I. Arquitetura em Camadas
O código MUST seguir camadas + casos de uso: Presentation (CLI) → Application (casos de uso:
varrer, curar, sintetizar, validar, publicar) → Domain (entidades, regras, value objects) →
Infrastructure (filesystem, repositório YAML, providers de IA). A Presentation MUST NOT conter
regra de negócio. O Domain MUST NOT depender de frameworks, CLI, logger concreto ou SDK externo,
e MUST NOT chamar logging. Toda integração externa MUST ser encapsulada na Infrastructure atrás
de porta/adapter; portas só existem onde há integração externa (sem abstração ornamental).
Nenhum provider de IA é fixado no núcleo: toda integração de IA MUST implementar a interface
Strategy/Adapter comum.
*Racional*: módulos coesos e substituíveis, testáveis isoladamente.

### II. Contratos Validados e Versionados
Toda entrada MUST ser validada antes de chegar ao Domain (pydantic/dataclasses, nunca checagens
espalhadas). Toda saída estruturada relevante — JSON, YAML ou frontmatter Markdown — MUST carregar
`schema_version` e ser validada por JSON Schema em `schemas/<dominio>-schema-v<major>.json`.
Mudança breaking exige novo arquivo com major incrementado; mudança aditiva não.
Os registros versionados vivem em `src/data` (`folders.yaml` e `sources/`).
*Racional*: só existe "dado válido" depois que o contrato o define.

### III. Test-First (NON-NEGOTIABLE)
Toda feature com regra de negócio MUST seguir a ordem: contrato/DTO → exceções semânticas →
testes de falha (vermelho, confirmados falhando) → implementação (verde) → refatoração.
Correção de bug MUST começar por um teste que reproduza a falha. Toda dependência externa
(pastas de origem, provider de IA, filesystem) MUST ter ao menos um teste simulando
indisponibilidade/timeout. Caminho feliz sozinho NÃO conta como cobertura. Implementação escrita
antes dos testes MUST ser descartada.
*Racional*: sem restrição explícita, o código nasce só com o caminho feliz.

### IV. Erros Semânticos nas Fronteiras
Domain e Application MUST levantar exceções específicas e nomeadas; nunca retornar `False`/`None`
como substituto genérico de erro. `try/except` MUST ficar nas fronteiras (CLI, I/O, integrações,
serialização), capturando exceções específicas — `BaseException` é proibido e `except Exception`
só é admitido como último recurso no `main()`. Erros MUST ser registrados com logs estruturados
(`exc_info=True`). Lotes MUST registrar a falha por item sem derrubar o lote inteiro.
*Racional*: o log precisa dizer se falhou validação ou rede.

### V. Proveniência, Licença e Localização das Fontes
Toda fonte curada MUST ter registro em `src/data/sources/<categoria>/<slug>.md` com origem, data,
licença por fonte (campo `license` obrigatório) e critério de relevância. Fonte sem licença
registrada MUST ficar com status "pendente" e MUST NOT gerar extrato copiado para o repositório.
Das fontes MUST ser extraídas só **ideias**: nenhum trecho literal, tradução ou paráfrase próxima de
terceiros entra no repositório, qualquer que seja a licença; a licença continua obrigatória no
registro, como informação, e não gradua a extração. O material bruto MUST permanecer fora do repo. O registro de pastas a curar MUST viver fora do
repositório: local padrão `$XDG_CONFIG_HOME/praxisforge/folders.yaml` (sem a variável,
`~/.config/praxisforge/folders.yaml`), substituível por `--registry` ou pela variável
`PRAXISFORGE_REGISTRY`. O repositório MUST NOT versionar registro de pastas com caminhos pessoais;
mantém apenas um exemplo sem caminhos pessoais (`src/data/folders.example.yaml`), validado no CI.
Cada pasta registrada MUST declarar seu caminho absoluto (campo obrigatório por item), que a
identifica de forma única junto com o `alias` — duas pastas não podem compartilhar o mesmo
caminho real nem estar uma dentro da outra. Registros de fonte (`src/data/sources/`) continuam
versionados no repositório. Caminho absoluto MUST NOT aparecer no código-fonte (nenhum caminho
fixo de máquina) e MUST NOT aparecer em logs ou mensagens de erro além do estritamente necessário
para identificar o próprio item com problema.
*Racional*: rastreabilidade e respeito a direitos; o caminho explícito elimina colisão entre
subpastas homônimas de raízes diferentes (23/09/2026); como o repositório é público e o registro
reflete a máquina de quem o mantém, ele fica fora do versionamento (24/09/2026). Só ideias (25/09/2026): síntese
autoral evita obra derivada e dispensa avaliar cada licença.

### VI. Acervo Versionado no Repositório
O repositório é a fonte de verdade do acervo em `library/`, com um diretório por tipo de recurso:
`skills`, `commands`, `agents`, `hooks`, `rules` e `references`, mais o índice `library/INDEX.md` e um
template por tipo. Todo item MUST passar por validação do seu tipo (formato, arquivos de apoio,
proveniência das fontes) antes de publicar. A publicação MUST ter como alvo apenas pastas de
projeto e MUST usar o comando de publicação do acervo (cópia/symlink idempotente); o escopo
global do usuário MUST NOT ser escrito. O vault Obsidian NÃO guarda cópias do acervo, apenas
catálogo e templates de criação.
*Racional*: histórico, revisão e CI só existem em git; cópias duplicadas geram drift; o objetivo é
uma base de conhecimento agnóstica, não a configuração pessoal do curador (25/09/2026).

### VII. Memória e Sessões no Vault Obsidian
Toda memória e registro de sessão MUST usar o vault `claude_memory`: sessões em `daily/`, dados do
projeto em `projects/`; toda nota nova MUST ser listada com descrição no `00-index.md`. Nenhum
token, senha, IP interno ou endpoint com credenciais pode ser gravado no vault ou no repo.
Credenciais MUST ficar em `.secrets/` (fora do git). Relatórios de erro e correção MUST ir para
`docs/bugs/`.
*Racional*: memória única, durável e sem vazamento de segredos.

## Restrições Adicionais

- Python 3.12+ gerenciado por `uv`; dependências em `pyproject.toml` e `uv.lock` versionado.
- Dependências-chave: pyyaml, pydantic, jsonschema, requests; qualidade: pytest, ruff, mypy.
- Requisições HTTP MUST usar Python (`requests`), nunca `curl` com credenciais.
- Organização: código em `src/`, scripts em `scripts/`, testes em `tests/`, docs em `docs/`;
  ADRs em `docs/decisions/` (MADR simplificado) e visão geral em `docs/architecture/overview.md`.
- Scripts MUST ser idempotentes e o ambiente MUST ser reproduzível do zero (clone limpo → setup).

## Fluxo de Desenvolvimento e Quality Gates

- Nenhum commit direto na `main`: branch de feature + pull request; commits Conventional Commits
  em pt-BR (tipos em inglês).
- Pre-commit MUST incluir lint, tipagem e GitGuardian (`ggshield secret scan pre-commit`);
  commit bloqueado por secret exige remover o secret e refazer; `--no-verify` é proibido.
  Secret já commitado MUST ser considerado comprometido e rotacionado.
- Gates bloqueantes: `ruff check .` e `ruff format` sem violações → `mypy` com 0 erros →
  `pytest --cov-fail-under=90`; `yamllint` e `check-jsonschema` nos YAML/JSON; `bandit` e `safety`.
- Planejamento por spec-driven development: constituição → specification → plan → tasks →
  implementation.
- Critério de sucesso do ciclo de curadoria (mensal): ≥ 95% das skills/agentes publicados
  aprovados na validação.

## Governance

Esta constituição prevalece sobre outras práticas do projeto. Emendas MUST ser documentadas
(ADR quando alterarem decisão arquitetural), revisadas em pull request e acompanhadas de plano de
migração quando afetarem código existente. Versionamento semântico: MAJOR para remoção ou
redefinição incompatível de princípios; MINOR para novo princípio/seção ou expansão material;
PATCH para esclarecimentos e ajustes de redação. Todo PR e revisão MUST verificar conformidade
com estes princípios; complexidade adicional MUST ser justificada. Orientação de execução
complementar: `objetivo-init-praxisforge.md` e `CLAUDE.md`.

**Version**: 4.0.0 | **Ratified**: 2026-09-18 | **Last Amended**: 2026-09-25
