<!-- Criado em: 21/09/2026 15:59 -->
<!-- Modificado em: 21/09/2026 16:09 -->

# Contrato da CLI — `praxisforge`

Interface pública desta feature. Presentation fina: só converte argumentos em DTOs, chama casos
de uso e traduz exceções em mensagens e códigos de saída.

## Comandos

| Comando | Efeito | Idempotente |
|---------|--------|-------------|
| `praxisforge folders add --alias A --description D --content-type T --license L [--status S]` | Registra pasta; cria o arquivo do registro se não existir. Alias idêntico com dados idênticos ⇒ "inalterado" | sim |
| `praxisforge folders list [--status S]` | Lista pastas (alias, tipo, licença, status, última varredura) | — |
| `praxisforge folders show ALIAS` | Mostra todos os dados de uma pasta (sem caminho absoluto) | — |
| `praxisforge folders update ALIAS [--status S] [--last-scanned ISO] [--license L]` | Atualiza campos informados (atômico) | sim |
| `praxisforge folders validate` | Valida o registro contra `folders-schema-v1`; lista todas as violações; agrega falhas por pasta | — |
| `praxisforge folders resolve ALIAS` | Resolve alias → caminho real via ambiente (única saída que imprime caminho) | — |
| `praxisforge sources validate PATH...` | Valida frontmatter de fontes (`source-schema-v1`); PATH = arquivo ou diretório; lote com falha por item | — |

Opções globais: `--registry PATH` (padrão `src/data/folders.yaml`), `--log-level`.

## Códigos de saída

| Código | Significado | Exemplos |
|--------|-------------|----------|
| 0 | Sucesso (inclui "inalterado") | registro válido |
| 1 | Falha de validação/negócio | contrato inválido, alias duplicado, pasta inexistente |
| 2 | Uso incorreto | argumento ausente ou inválido |
| 3 | Falha de ambiente | variável ausente, caminho inacessível, registro ilegível |

## Mensagens

- Erros em `stderr`, em pt-BR, com o alias e o motivo; nunca caminho absoluto exceto em
  `folders resolve`.
- `validate` lista **todas** as violações (campo + motivo) e ao final um resumo
  `N ok, M com falha`.
- Datas exibidas em `DD/MM/AAAA HH:MM` (America/Sao_Paulo); armazenadas em ISO 8601 com offset.

## Contratos de dados

- Registro: [folders-schema-v1.json](folders-schema-v1.json)
- Fonte: [source-schema-v1.json](source-schema-v1.json)
- Variável de ambiente por alias: `PRAXISFORGE_FOLDER_<ALIAS EM MAIÚSCULAS>` (absoluta, sem `..`)

Os arquivos em `contracts/` são o rascunho de projeto; a implementação os publica em
`schemas/` (fonte de verdade em runtime) e um teste de contrato garante que não divergem.
