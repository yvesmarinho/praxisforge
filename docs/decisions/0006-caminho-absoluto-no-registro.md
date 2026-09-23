<!-- Criado em: 23/09/2026 17:05 -->
<!-- Modificado em: 23/09/2026 17:05 -->

# ADR 0006: Caminho absoluto no registro de pastas

## Status

Aceito (23/09/2026) — feature `005-caminho-absoluto-registro`; constituição v2.0.0 (Princípio V).

## Contexto

O registro guardava só o alias, derivado do nome da subpasta, e o caminho real vinha de uma
variável de ambiente por alias (`PRAXISFORGE_FOLDER_<ALIAS>`). Duas subpastas homônimas de
pastas-raiz diferentes colidiam no bootstrap, e manter uma variável por pasta não escalava
(registro local com 55 pastas).

## Decisão

- `folders-schema-v2.json`: campo `path` **obrigatório** (absoluto, canônico); `schema_version: "2"`.
  Mudança incompatível → novo major (constituição II). A v1 é lida apenas por `folders migrate`.
- `FolderRegistry` garante caminho único **e sem aninhamento**, comparando por componentes e sem
  diferenciar maiúsculas/minúsculas.
- Porta `FolderLocator` (adapter `FilesystemFolderLocator`) canoniza (`~`, relativo, `..`, links) e
  confere o caminho registrado; `PathResolver`/`EnvPathResolver` e `FolderPathNotConfiguredError`
  foram removidos. Variáveis antigas só são lidas pela migração (`LegacyPathSource`).
- Bootstrap: alias `<raiz>__<subpasta>` (normalizados; prefixo `p` para vazio/dígito), sufixo
  `_2`, `_3`… quando ocupado, truncamento para 63 caracteres; identidade pelo caminho; a raiz
  nunca é registrada.
- `folders migrate [--root]`: caminho pela variável antiga, senão pela subpasta da raiz com o
  mesmo nome normalizado; raiz registrada como pasta é removida; grava só sem pendências.
- `folders update --path` corrige pasta movida preservando os demais dados.

## Alternativas consideradas

- **Raiz + caminho relativo** (`root` + `path`, uma variável por raiz): mantinha o YAML portável
  entre máquinas; rejeitada pelo usuário.
- **Caminho com `~`**: não expõe o usuário, mas continua dependente da estrutura da máquina.
- **Manter variáveis como sobrescrita opcional**: duas fontes de verdade; rejeitada.

## Consequências

- O `folders.yaml` versionado passa a refletir a máquina de quem o mantém.
- Todo comando usa só o registro — zero configuração por pasta.
- Registros v1 exigem `praxisforge folders migrate` antes de qualquer outro comando.
