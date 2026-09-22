<!-- Criado em: 22/09/2026 10:15 -->
<!-- Modificado em: 22/09/2026 10:13 -->

# ADR 0004: `folders update` aceita licença além de status e última varredura

## Status

Aceito (22/09/2026)

## Contexto

FR-002 (spec original) cita apenas `status` e `last_scanned` como campos
atualizáveis. Porém a invariante de `Folder` exige que licença `unknown`
implique status `pending`; sem poder atualizar a licença na mesma operação,
uma pasta como `github_forks` (licença `unknown`) ficaria permanentemente
presa em `pending`, sem caminho para sair desse estado.

## Decisão

`FolderRegistry.update` (e o DTO `UpdateFolderInput`) aceita opcionalmente
`license` além de `status` e `last_scanned`. A operação é atômica: a mudança
inteira (todos os campos informados) é aplicada de uma vez, e as invariantes
de `Folder` são reavaliadas sobre o resultado final — permitindo, por exemplo,
atualizar `license` e `status` na mesma chamada quando a licença `unknown` é
resolvida (spec US1, cenário 5).

## Consequências

- Extensão pequena do escopo original da FR-002, mas necessária para que o
  registro inicial (`github_forks`, licença `unknown`) tenha um caminho de
  saída de `pending` sem exigir remover e recriar a pasta.
- Documentada em `data-model.md` como parte do contrato de `FolderRegistry.update`.
