<!-- Criado em: 22/09/2026 16:58 -->
<!-- Modificado em: 22/09/2026 14:57 -->

# Contrato de Interface: `praxisforge folders bootstrap`

Nenhum schema JSON novo é criado — `schemas/folders-schema-v1.json` é alterado **no lugar**, de
forma aditiva (ver [data-model.md](../data-model.md)). O contrato exposto ao usuário é a interface
de linha de comando abaixo, mais o efeito sobre `folders scan --all` (feature 002).

## `folders bootstrap <root>`

Varre a pasta-raiz `<root>` e registra as subpastas de primeiro nível ainda não conhecidas.

- **Entrada**: `root` (posicional, obrigatório) — caminho para uma pasta-raiz existente e legível.
  Não precisa estar associado a nenhum alias/variável de ambiente; é usado diretamente.
- **Saída (sucesso, exit code 0)**: resumo com contagem de pastas **registradas**, **já
  existentes** (puladas), **ignoradas** (`status: ignore`, puladas) e **com falha**; lista cada
  alias novo registrado; lista cada falha individual com o nome da subpasta e o motivo. Nenhuma
  saída contém caminho absoluto, exceto quando citando o caminho de uma subpasta especificamente
  na mensagem de erro daquela subpasta (FR-014).
- **Saída (falha, exit code 1)**: `root` não existe, não é diretório, ou sem permissão de leitura
  → operação inteira recusada citando o motivo (falha de item individual não se aplica aqui —
  é a pré-condição da execução inteira).
- **Garantia de idempotência**: rodar o mesmo comando duas vezes seguidas sem mudança no
  filesystem produz o mesmo `folders.yaml` na segunda vez — nenhuma pasta já registrada
  (`skipped_existing`/`skipped_ignored`) é modificada (FR-004, SC-002).
- **Garantia**: o bootstrap nunca atribui `status: ignore` a nenhuma pasta (FR-012) — esse valor
  só existe no registro se o curador o aplicou manualmente via `folders update`.

## Efeito sobre `folders scan --all` (feature 002, alterado por esta feature)

- Pastas com `status: ignore` são puladas — não entram na contagem de "ok" nem "com falha";
  aparecem numa nova linha do resumo como "ignoradas" (FR-013).
- `folders scan <alias>` (varredura **individual** e explícita) continua funcionando
  normalmente mesmo para um alias `ignore` — a checagem de pular só se aplica ao modo `--all`.

## `folders update --status ignore` (reaproveita o subcomando já existente, feature 001)

- Novo valor de `--status` aceito: `ignore`.
- Pode ser aplicado mesmo quando `license` atual é `unknown` (a invariante "unknown ⇒ pending"
  passa a admitir também `ignore` — FR-011).

## Exit codes (reaproveitados das features 001/002)

| Código | Significado |
|---|---|
| 0 | bootstrap concluído (mesmo com falhas de item individuais, que são reportadas mas não impedem a execução) |
| 1 | falha de pré-condição da execução inteira (`root` inválido/inacessível) ou falha de validação/negócio em `folders update` |
| 2 | uso incorreto da CLI |
| 3 | falha de ambiente (não se aplica diretamente ao bootstrap, que não usa `PRAXISFORGE_FOLDER_*`; reaproveitado por `folders scan`/`resolve` como já documentado) |
