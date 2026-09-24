<!-- Criado em: 24/09/2026 10:13 -->
<!-- Modificado em: 24/09/2026 10:13 -->

# Registro inválido gera traceback no scan/resolve; ELv2 não reconhecida no bootstrap

## Sintoma

Após o bootstrap, `praxisforge folders scan --all` terminou com traceback Python
(`ContractValidationError`) em vez de mensagem amigável. O `folders.yaml` tinha 5 pastas fora
do contrato v2:

- 2 com `license: unknown` e `status: not_scanned` (o contrato exige `pending` ou `ignore`);
- 1 com o mesmo problema, mas cujo LICENSE é Elastic License 2.0 — o bootstrap não a reconheceu;
- 2 com `description` vazia.

O bootstrap grava `pending` quando a licença é `unknown`, então os estados inválidos vieram
de edição manual posterior do YAML.

## Causa

1. `_cmd_folders_scan` e `_cmd_folders_resolve` (`presentation/cli.py`) só tratavam
   `FolderNotFoundError` e erros de ambiente; `ContractValidationError` (e demais
   `PraxisForgeError` do `load()`) escapavam até o interpretador. Os outros comandos já
   tratavam `PraxisForgeError`.
2. `FilesystemFolderProbe` não tinha assinatura para a Elastic License 2.0.

## Correção

1. `_falha_de_registro()` na CLI: imprime o erro no stderr, sugere
   `praxisforge folders validate` quando é violação de contrato e sai com código 1 — aplicada
   a `scan` e `resolve`, individual e `--all`.
2. Assinatura `"Elastic-2.0": ("elastic license 2.0",)` no detector de licenças.
3. Dados (registro local, não versionado — repositório público): 2 pastas sem LICENSE voltaram a `pending`; `context_mode` recebeu
   `license: Elastic-2.0`; as 2 descrições vazias foram preenchidas a partir do README.

Observação: a ELv2 não é open source (restringe oferta como serviço gerenciado); avaliar antes
de copiar extratos dessa fonte.

## Verificação

- Testes vermelhos antes da correção: `test_scan_registro_invalido_codigo_1_sem_traceback`,
  `test_resolve_registro_invalido_codigo_1_sem_traceback` (alias e `--all`) e o caso
  Elastic-2.0 em `test_detect_license_reconhece_licencas_suportadas`.
- `folders validate`: 53 ok; `folders scan --all`: 18 ok, 35 ignoradas, 0 falhas.
