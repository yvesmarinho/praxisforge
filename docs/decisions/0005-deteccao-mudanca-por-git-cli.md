<!-- Criado em: 23/09/2026 12:17 -->
<!-- Modificado em: 23/09/2026 12:17 -->

# ADR 0005: Detecção de mudança de conteúdo pós-curadoria via executável git

## Status

Aceito (23/09/2026) — feature `004-deteccao-mudanca-conteudo`

## Contexto

`last_scanned` só confirmava que o caminho de uma pasta continua acessível; uma pasta `curated`
podia receber novos commits e permanecer `curated` indefinidamente. Era preciso registrar qual
versão do conteúdo foi revisada e detectar, na varredura, quando ela mudou — sem acrescentar
dependências e sem gerar reversões falsas em pastas que são subpastas de repositórios maiores.

## Decisão

- Novo campo **opcional** `last_curated_commit` em `folders-schema-v1.json` (SHA-1 ou SHA-256,
  hex minúsculo). Mudança aditiva pelo critério da feature 003 → permanece v1; registros antigos
  validam sem migração.
- O hash é gravado ao marcar a pasta como `curated` (`folders update`) e mantido como histórico
  nos demais status.
- Na varredura, pasta `curated` com hash é comparada com o HEAD **restrita à própria pasta**
  (`git diff --quiet <hash> HEAD -- .`); mudou → `in_curation`. Hash ausente do histórico conta
  como mudança. Alterações não commitadas não contam.
- Pasta `curated` sem hash (legado) recebe o HEAD atual como referência na primeira varredura.
- Integração atrás da porta `GitContentInspector`; adapter `GitCliInspector` chama o executável
  `git` via `subprocess` (lista de argumentos, `shell=False`, timeout de 10 s, hash validado por
  regex antes de ir para a linha de comando).

## Alternativas consideradas

- **GitPython / pygit2**: dependência nova (pygit2 com biblioteca nativa); GitPython também chama
  o executável por baixo.
- **Comparar só o HEAD**: gera reversão falsa quando a pasta é subpasta e o commit mexe fora dela.
- **`folders-schema-v2.json` com campo obrigatório**: exigiria migração do registro sem ganho.

## Consequências

- `git` ≥ 2.x passa a ser pré-requisito para verificar pastas curadas; ausência dele é falha de
  verificação (exit 3 no individual, falha por item no lote), nunca "pasta não-git".
- `update_folder()` e `scan_*()` recebem `PathResolver`/`GitContentInspector`; marcar `curated`
  exige o caminho configurado (`PRAXISFORGE_FOLDER_<ALIAS>`).
- Bandit: `# nosec B404/B603/B607` justificados no adapter.
