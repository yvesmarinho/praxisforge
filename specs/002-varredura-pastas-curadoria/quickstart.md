<!-- Criado em: 22/09/2026 11:59 -->
<!-- Modificado em: 22/09/2026 11:50 -->

# Quickstart: Varredura das Pastas Registradas

Guia de validação manual end-to-end da feature 002, após a implementação (`/speckit-implement`).

## Pré-requisitos

- Feature 001 implementada e mergeada (`FolderRegistry`, `PathResolver`, CLI `folders add/update`
  já funcionando).
- Ambiente instalado: `make install-deps` (ou `uv sync`).
- Pelo menos um diretório real no filesystem para apontar via variável de ambiente.

## Cenário 1 — Varrer uma pasta (US1)

```bash
mkdir -p /tmp/praxisforge-demo/pasta-a
export PRAXISFORGE_FOLDER_DEMO_A=/tmp/praxisforge-demo/pasta-a

uv run praxisforge folders add --alias demo_a --description "Demo" \
  --content-type documents --license MIT

uv run praxisforge folders scan demo_a
```

**Esperado**: saída confirma `status: varrida` e `last_scanned` com a data/hora atual;
`uv run praxisforge folders show demo_a` reflete a mudança. Ver [spec.md](./spec.md) cenários 1-2.

Rodar de novo (`folders scan demo_a`) → status permanece `varrida`, só `last_scanned` avança
(cenário 2).

## Cenário 2 — Alias inexistente / caminho quebrado (US1, falhas)

```bash
uv run praxisforge folders scan alias_nao_registrado   # exit code 1, cita o alias
unset PRAXISFORGE_FOLDER_DEMO_A
uv run praxisforge folders scan demo_a                  # exit code 1, cita o motivo
```

**Esperado**: em ambos os casos, `folders show demo_a` (quando aplicável) mostra o registro
inalterado. Ver spec cenários 3-4.

## Cenário 3 — Varredura em lote (US2)

```bash
export PRAXISFORGE_FOLDER_DEMO_A=/tmp/praxisforge-demo/pasta-a
mkdir -p /tmp/praxisforge-demo/pasta-b
export PRAXISFORGE_FOLDER_DEMO_B=/tmp/praxisforge-demo/pasta-b
uv run praxisforge folders add --alias demo_b --description "Demo B" \
  --content-type documents --license MIT

uv run praxisforge folders add --alias demo_quebrada --description "Quebrada" \
  --content-type documents --license MIT
# sem exportar PRAXISFORGE_FOLDER_DEMO_QUEBRADA de propósito

uv run praxisforge folders scan --all
```

**Esperado**: resumo final reporta 2 pastas atualizadas e 1 com falha (`demo_quebrada`, motivo
citado); nenhuma interrupção do lote. Ver spec cenário 5 / SC-002.

## Cenário 4 — Detecção de aliases duplicados (US3)

```bash
export PRAXISFORGE_FOLDER_DEMO_DUP=/tmp/praxisforge-demo/pasta-a   # mesmo caminho de demo_a
uv run praxisforge folders add --alias demo_dup --description "Duplicada" \
  --content-type documents --license MIT

uv run praxisforge folders scan --all
```

**Esperado**: relatório final lista o par `demo_a` / `demo_dup` como grupo duplicado, sem impedir
que ambos sejam varridos com sucesso. Rodar `folders scan --all` de novo → a duplicidade
continua sendo reportada (não é persistida). Ver spec cenário 6 / SC-003.

## Verificação de segurança (SC-004)

```bash
uv run praxisforge folders scan --all | grep -F "/tmp/praxisforge-demo"
```

**Esperado**: nenhuma linha da saída normal contém o caminho absoluto — só mensagens de erro
específicas de uma pasta (quando aplicável) podem citá-lo.

## Limpeza

```bash
rm -rf /tmp/praxisforge-demo
unset PRAXISFORGE_FOLDER_DEMO_A PRAXISFORGE_FOLDER_DEMO_B PRAXISFORGE_FOLDER_DEMO_DUP
```

## Referências

- Contrato de CLI: [contracts/cli-scan.md](./contracts/cli-scan.md)
- Modelo de dados: [data-model.md](./data-model.md)
- Decisões técnicas: [research.md](./research.md)
