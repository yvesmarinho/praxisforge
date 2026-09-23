<!-- Criado em: 23/09/2026 13:03 -->
<!-- Modificado em: 23/09/2026 13:03 -->

# Contrato CLI — caminho no registro

Exit codes: 0 ok · 1 validação/negócio · 2 uso · 3 ambiente (pasta inacessível, git).

| Comando | Mudança |
|---|---|
| `folders add --alias A --path P ...` | `--path` obrigatório; canonizado; inexistente/não-pasta → exit 3; já registrado → exit 1 citando o alias ocupante |
| `folders update A --path P` | novo caminho, mesmas validações; demais dados preservados |
| `folders list` | nova coluna com o caminho |
| `folders show A` | nova linha `caminho: <P>` |
| `folders resolve A\|--all` | usa o caminho do registro; pasta movida → exit 3 |
| `folders scan`, `update --status curated` | usam o caminho do registro; nenhuma variável de ambiente |
| `folders bootstrap ROOT` | alias `<raiz>__<sub>`; idempotente por caminho; saída só com alias |
| `folders migrate [--root DIR]` | **novo**: v1 → v2; lista migradas e pendentes; grava só sem pendências (exit 0), senão exit 1 sem gravar; já v2 → "registro já no formato atual", exit 0 |
| qualquer comando com registro v1 | exit 1: "registro no formato v1 — execute: praxisforge folders migrate" |
