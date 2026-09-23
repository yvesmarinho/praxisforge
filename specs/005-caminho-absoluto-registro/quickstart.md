<!-- Criado em: 23/09/2026 13:03 -->
<!-- Modificado em: 23/09/2026 13:03 -->

# Quickstart: validação ponta a ponta da feature 005

Usar sempre `--registry <tmp>/folders.yaml` e pastas em diretório temporário.

1. **Registro com caminho (US1)**: `folders add --alias demo --path <tmp>/demo ...` → `show demo`
   exibe `caminho:`; `scan demo` funciona sem nenhuma variável `PRAXISFORGE_FOLDER_*`.
2. **Duplicidade**: `folders add --alias outro --path <tmp>/demo` → exit 1 citando `demo`.
3. **Bootstrap sem colisão (US2)**: raízes `r1/graphify` e `r2/graphify` → `bootstrap r1` e
   `bootstrap r2` registram `r1__graphify` e `r2__graphify`; repetir → nada muda.
4. **Pasta movida**: mover `<tmp>/demo` → `scan demo` exit 3; `update demo --path <novo>` → ok,
   status/versão curada preservados.
5. **Migração (US3)**: registro v1 com 3 pastas (uma com variável de ambiente, uma encontrável na
   raiz, uma sem caminho) → `migrate --root <raiz>` exit 1 listando 1 pendente e sem gravar;
   resolver a pendência → `migrate` exit 0, registro v2 válido; repetir → "já no formato atual".
6. **Registro v1 em outro comando**: `folders list` → exit 1 pedindo migração.
7. Gates: `make lint`, `make test` (≥ 90%), `make validate-data`, `make security`.
