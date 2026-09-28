<!-- Criado em: 28/09/2026 16:31 -->
<!-- Modificado em: 28/09/2026 16:31 -->

# Triar a curadoria com LLM

A triagem lê cada artefato pendente do inventário e diz se a ideia dele **já existe no acervo**
(`covered`), **falta no acervo** (`gap`) ou **não é conhecimento curável** (`out_of_scope`). Para
cada lacuna, ela escreve um rascunho autoral só com as ideias. Nada entra no repositório: vereditos
e rascunhos ficam em `~/.config/praxisforge/curation/`, esperando a revisão (feature 012).

## Pré-requisitos

1. Pasta inventariada: `praxisforge curation inventory <alias>` (guia
   [inventariar-curadoria.md](inventariar-curadoria.md)).
2. CLI `claude` instalado e autenticado (`claude /login`). A triagem recusa versões fora da faixa
   testada (hoje 2.1.x a partir de 2.1.283).
3. Rodar na raiz do repositório, ou definir `PRAXISFORGE_ROOT`: os prompts vêm de
   `prompts/curation/`.

## Uso

```bash
praxisforge curation triage github_forks__andrej_karpathy_skills --max-calls 10
praxisforge curation triage --all --max-calls 200 --max-cost-usd 1
praxisforge curation status
```

| Opção | Padrão | Para quê |
|---|---|---|
| `--max-calls N` | 50 | teto de chamadas nesta execução (todas as pastas somadas) |
| `--max-cost-usd X` | — | teto em US$ (o CLI informa o custo de cada chamada) |
| `--triage-model` / `--draft-model` | `haiku` / `sonnet` | modelos da triagem (e do juiz) e do rascunho |
| `--timeout S` | 120 | timeout por chamada |
| `--similarity-threshold T` | 0,7 | limiar da verificação estrutural |
| `--retry-failed` | — | tenta de novo artefatos que falharam 3 vezes |
| `--max-consecutive-failures K` | 5 | para depois de K indisponibilidades seguidas |
| `--allow-untested-cli` | — | aceita um CLI fora da faixa testada (rode antes o teste `live`) |

## Teto e retomada

A execução nunca passa do teto. Ao atingi-lo, ela sai com código **4** e mostra o comando para
continuar, que é o mesmo comando: o que já foi triado ou rascunhado não é reenviado. Uma lacuna
triada sem orçamento para o rascunho fica `triaged`, e a próxima execução só rascunha.

## Lendo o resultado

- `curation status` mostra, por pasta, as etapas e as colunas `COB`, `LAC` e `FORA` (vereditos) e
  `ALERTA` (rascunhos que continuaram parecidos demais com o original depois da regeneração).
- Rascunhos: `~/.config/praxisforge/curation/_drafts/<id>.json`, com proposta, origens e as
  verificações de similaridade.
- Códigos de saída: 0 ok · 1 falha de dados ou de artefato · 2 uso · 3 ambiente (CLI ausente ou
  não verificado, prompt faltando, lock, falhas consecutivas) · 4 teto · 130 interrompido.

## Mudando prompts ou critérios

Os prompts ficam em `prompts/curation/` e fazem parte do código (passam por PR). Cada veredito
guarda a impressão digital do conjunto; ao mudar qualquer prompt, os artefatos ainda não revisados
voltam para a triagem na próxima execução.

## O que sai da máquina

Para o serviço do modelo vão: o conteúdo do artefato, o alias e o caminho relativo dele, o índice
e itens do acervo público, o índice dos rascunhos pendentes e os prompts. Não vão: caminhos
absolutos, o registro, variáveis de ambiente nem outros arquivos de `~/.config`.

## Segurança

O modelo roda sem nenhuma ferramenta: não executa comandos nem lê ou grava arquivos. Só o
praxisforge grava, e só dentro de `curation/`. Antes de ampliar a faixa de versões do CLI no
código, rode `uv run pytest -m live tests/live` (custo de alguns centavos).
