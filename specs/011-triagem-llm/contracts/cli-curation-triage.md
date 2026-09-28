<!-- Criado em: 28/09/2026 15:32 -->
<!-- Modificado em: 28/09/2026 15:40 -->

# Contrato da CLI: `praxisforge curation triage`

Opção global herdada: `--registry <arquivo>`, que define onde ficam `curation/<alias>/` e
`curation/_drafts/`.

## `curation triage (<alias> | --all) [opções]`

Tria os artefatos elegíveis (FR-002) de uma pasta inventariada, ou de todas as inventariadas,
exceto `ignore`. Gera rascunhos para as lacunas e grava o estado após cada artefato.

| Opção | Padrão | Efeito |
|---|---|---|
| `--max-calls N` | 50 | teto de chamadas ao modelo nesta execução (N ≥ 1) |
| `--max-cost-usd X` | — | teto de custo em US$ (X > 0) |
| `--triage-model M` | `haiku` | modelo da triagem e do juiz |
| `--draft-model M` | `sonnet` | modelo do rascunho |
| `--timeout S` | 120 | timeout por chamada, em segundos (S ≥ 10) |
| `--similarity-threshold T` | 0.7 | limiar estrutural (0 < T ≤ 1) |
| `--retry-failed` | desligado | inclui `failed` com 3 tentativas ou mais |
| `--max-consecutive-failures K` | 5 | para após K indisponibilidades seguidas |
| `--allow-untested-cli` | desligado | aceita versão do `claude` fora da faixa testada (FR-037); os flags de isolamento continuam obrigatórios |

Saída (stdout):

```text
<alias>: 12 triados (3 cobertos, 7 lacunas, 2 fora de escopo), 7 rascunhos (1 com alerta), 1 falha, 38 restantes
<alias>: FALHA — <motivo sem caminho absoluto>
Resumo: 50 chamadas, US$ 0,27, parada: teto de chamadas
Para continuar: praxisforge curation triage <alias>
```

Se o custo não for informado: `custo: não mensurável (teto em US$ ignorado)`. Falhas por artefato
vão para stderr, uma linha cada: `<alias>:<caminho relativo>: <tipo do erro>`.

| Exit | Quando |
|---|---|
| 0 | todos os elegíveis foram processados, sem falha |
| 1 | alias inexistente; pasta nunca inventariada; estado corrompido; rascunho corrompido em `_drafts/` (antes da 1ª chamada, com o `draft_id`); ≥ 1 artefato ou pasta com falha |
| 2 | uso: sem alvo, `<alias>` e `--all` juntos, opção fora do intervalo |
| 3 | ambiente: `claude` ausente ou fora da faixa testada, flag de isolamento recusado, prompt ausente ou vazio, lock ocupado, link simbólico em `curation/`, falhas consecutivas, registro ilegível |
| 4 | teto atingido (chamadas ou custo); o estado está gravado e a retomada é o mesmo comando |
| 130 | interrompido (Ctrl+C); o estado gravado até o artefato anterior fica íntegro |

Garantias:

- nenhuma escrita fora de `<dir do registro>/curation/` (SC-006);
- nenhuma escrita na pasta curada nem no repositório;
- cada chamada ao modelo usa os flags de isolamento de [research.md](../research.md) R1;
- nenhum caminho absoluto aparece na saída.

## `curation status` (010, estendido)

Novas colunas após as da 010:

```text
ALIAS            SITUAÇÃO    PEND TRIA RASC REVI PROM FALH DESC REMO  COB  LAC FORA ALERTA
agent_skills     incompleta    41    3    7    0    0    1    0    2    3    7    2      1
```

`--json` ganha, por pasta: `verdicts: {covered, gap, out_of_scope}` e `similarity_alerts`.
