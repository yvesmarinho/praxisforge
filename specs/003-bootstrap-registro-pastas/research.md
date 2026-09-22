<!-- Criado em: 22/09/2026 16:52 -->
<!-- Modificado em: 22/09/2026 14:57 -->

# Research: Bootstrap do Registro de Pastas

## Decisão 1 — Nova porta `RootFolderProbe`, em vez de reaproveitar `PathResolver`

- **Decision**: criar uma porta nova em `application/ports.py`, `RootFolderProbe`, com três
  métodos: `list_subfolders(root: Path) -> list[Path]`, `read_description(path: Path) -> str |
  None`, `detect_license(path: Path) -> str | None`.
- **Rationale**: `PathResolver.resolve(alias)` resolve **um alias já registrado** a partir de uma
  variável de ambiente — não serve para "listar subpastas de uma raiz arbitrária recebida como
  argumento". São operações de infraestrutura conceitualmente diferentes (resolução por alias vs.
  varredura de diretório + leitura de arquivos de texto); separar evita forçar uma porta existente
  a fazer algo fora do seu contrato original.
- **Alternatives considered**: estender `PathResolver` com um método opcional de listagem
  (rejeitado — violaria Interface Segregation sem necessidade; `EnvPathResolver` não teria como
  implementar "listar subpastas de uma raiz arbitrária" de forma coerente com seu propósito atual).

## Decisão 2 — Heurística de licença por comparação de texto, sem biblioteca nova

- **Decision**: `detect_license()` lê o conteúdo de `LICENSE`/`LICENSE.md`/`LICENSE.txt` (primeiro
  que existir) e compara com um pequeno dicionário de assinaturas textuais por licença:
  - MIT: contém `"permission is hereby granted, free of charge"` (case-insensitive)
  - Apache-2.0: contém `"apache license"` e `"version 2.0"`
  - GPL-3.0: contém `"gnu general public license"` e `"version 3"`
  - BSD-3-Clause: contém `"redistribution and use in source and binary forms"` e
    `"neither the name of"`
  Nenhuma correspondência confiável → retorna `None` (a Application trata como `license: "unknown"`
  + `status: PENDING`, conforme FR-007).
- **Rationale**: mantém a filosofia de dependências mínimas do projeto (nenhuma lib de
  identificação SPDX adicionada); um falso negativo (licença real não reconhecida) é seguro — cai
  em `unknown`/`pending` para revisão manual, nunca é adivinhado errado.
- **Alternatives considered**: biblioteca de identificação de licença via SPDX (rejeitado
  explicitamente pelo usuário — adiciona dependência nova fora do padrão do projeto).

## Decisão 3 — Extração de `description` a partir do README

- **Decision**: `read_description()` lê `README.md`/`README`/`README.rst` (primeiro que existir),
  ignora linhas vazias e linhas que são só um cabeçalho Markdown (`^#+\s`) ou uma imagem/badge
  (`^\[!\[`/`^!\[`) no início do arquivo, e retorna o primeiro parágrafo de texto útil encontrado,
  truncado em 500 caracteres (limite do contrato, já validado por `Folder.__post_init__`). Se
  nenhum README existir, retorna `None` e a Application usa uma descrição padrão (ex.:
  `"Pasta descoberta pelo bootstrap; sem README para extrair descrição"`).
- **Rationale**: primeiro parágrafo de texto real (não título, não badge) é a heurística mais
  simples que produz uma descrição minimamente útil sem exigir parsing de Markdown completo.
- **Alternatives considered**: usar sempre a primeira linha não vazia, sem filtrar cabeçalhos/badges
  (rejeitado — na prática README's quase sempre começam com `# Nome do Projeto` e um badge de CI,
  que não são descrições úteis).

## Decisão 4 — Derivação de alias a partir do nome da subpasta (slugificação)

- **Decision**: nome da subpasta → minúsculas → espaços e hífens viram `_` → caracteres fora de
  `[a-z0-9_]` são removidos → resultado validado pela própria classe `Alias` (já existente,
  padrão `^[a-z][a-z0-9_]{1,62}$`). Se o resultado não passar na validação (ex.: começa com
  dígito, fica vazio, ou tem só 1 caractere), a subpasta é reportada como falha individual
  (`InvalidAliasError`, já existente) — não é normalizado à força além disso.
- **Rationale**: reaproveita 100% a validação já existente em `domain/alias.py`; nenhuma regra
  nova de formato de alias é criada, só a transformação de "nome de pasta" para "candidato a
  alias".
- **Alternatives considered**: gerar um alias sintético (ex.: hash) quando a slugificação falhar
  (rejeitado — esconderia o problema do curador; melhor falhar explicitamente e deixar o registro
  manual resolver o nome).

## Decisão 5 — Idempotência: registry.add() já garante não sobrescrever

- **Decision**: para cada subpasta, `bootstrap_folders()` primeiro verifica se o alias já existe
  no `FolderRegistry` carregado no início da execução (`existing_at_start = set(registry.folders)`
  antes do loop). Se existir e o status for `IGNORE`, conta como "ignorada"; se existir com
  qualquer outro status, conta como "já existente, pulada" — em nenhum dos dois casos o método
  `add()`/`update()` é chamado para esse alias. Só aliases realmente novos chegam a
  `FolderRegistry.add()`.
- **Rationale**: embora `FolderRegistry.add()` já seja idempotente para dados **idênticos** (dos
  testes da feature 001), o bootstrap precisa do comportamento mais forte de "nunca tentar
  recalcular/reescrever uma pasta existente" — mesmo que o README tenha mudado desde o registro
  original, o bootstrap não deve tocar nela (FR-004). Checar `existing_at_start` explicitamente
  evita qualquer ambiguidade.
- **Alternatives considered**: confiar só na idempotência de `add()` (rejeitado — `add()` levanta
  `AliasAlreadyRegisteredError` se os dados recalculados pelo bootstrap diferirem dos já
  registrados, o que faria uma pasta já curada aparecer como "falha" em vez de "pulada, sem
  mudança" — semântica errada para FR-004).

## Decisão 6 — Colisão de alias **dentro da mesma execução** vs. alias já existente

- **Decision**: se duas subpastas diferentes, ambas novas (nenhuma em `existing_at_start`),
  slugificam para o mesmo alias, a primeira é registrada normalmente; a segunda tentativa de
  `registry.add()` levanta `AliasAlreadyRegisteredError` (comportamento já existente do domínio,
  sem mudança) e é capturada como falha individual (FR-008), distinta de "já existente, pulada".
- **Rationale**: reaproveita a exceção de domínio já existente sem criar uma nova; a distinção
  "pulada" vs. "falha de colisão" é só uma questão de contagem na Application (`existing_at_start`
  antes do loop vs. exceção capturada durante o loop), não exige nenhuma mudança de contrato.

## Decisão 7 — Varredura (feature 002) pula pastas `ignore`

- **Decision**: `scan_all_folders()` passa a checar `folder.status is CurationStatus.IGNORE` antes
  de chamar `resolver.resolve()`; se for `ignore`, não tenta resolver, não conta como `ok` nem
  `failures` — soma em um novo campo `ScanBatchReport.ignored: list[str]` (aliases). A varredura
  individual (`scan_folder(alias)`) **não** ganha essa checagem — se o curador pedir explicitamente
  para varrer um alias específico marcado `ignore`, a operação segue normalmente (só o modo lote
  pula automaticamente, conforme FR-013 fala de "varredura em lote").
- **Rationale**: `ScanBatchReport` já existe e é um dataclass da feature 002; adicionar um campo
  com `default_factory=list` é uma extensão aditiva, sem quebrar nenhum teste/consumidor existente
  (mesmo padrão usado para adicionar `duplicates` na própria feature 002).
- **Alternatives considered**: fazer `scan_folder()` individual também recusar pastas `ignore`
  (rejeitado — FR-013 fala especificamente de varredura em lote; a spec não pede recusar a
  varredura individual explícita, e negar isso removeria uma via de escape legítima do curador).

**Output**: todas as decisões técnicas resolvidas; nenhum `NEEDS CLARIFICATION` restante.
