<!-- Criado em: 24/09/2026 10:41 -->
<!-- Modificado em: 24/09/2026 10:42 -->

# Contrato CLI — feature 006

| Comando | Comportamento |
|---|---|
| `sources validate PATH...` | valida cada `.md` com schema v2 **e** regras de domínio; uma linha `<arquivo>: <motivo>` por falha; resumo `N ok, M com falha`; exit 0 sem falhas, 1 com falhas |
| `sources validate` em registro v1 | falha do arquivo: `source-schema-v1 não é mais aceito — use extract_policy (source-schema-v2)`; exit 1 |
| `sources validate` em diretório vazio | `0 ok, 0 com falha`, exit 0 |
| `folders show A` | nova linha `política máxima: <link\|summary\|verbatim>`; sufixo ` (licença não classificada)` quando for o caso |
| `folders list` | nova coluna com a política máxima **após o status**; caminho continua a última coluna |

Mensagem de política excedida (exemplo):

```text
fonte.md: política 'verbatim' excede a máxima 'summary' para a licença Elastic-2.0 (escopo: code)
```

Licença não classificada: nenhum aviso em `sources validate` (Clarificação Q3).
