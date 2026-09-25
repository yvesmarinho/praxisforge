<!-- Criado em: 25/09/2026 09:58 -->
<!-- Modificado em: 25/09/2026 09:58 -->

# ADR 0010: Raiz do projeto por marcador, não pelo diretório atual

## Status

Aceito (25/09/2026). Resolve as limitações registradas nas features 007 e 008.

## Contexto

A CLI resolvia `schemas/`, `skills/`, `src/data/sources/` e o registro antigo
(`src/data/folders.yaml`) a partir do diretório atual. Fora da raiz do repositório, os comandos
falhavam ou, no caso do `skills catalog`, podiam gravar no lugar errado. O `scripts/publish-skills`
contornava o problema entrando na raiz antes de rodar.

## Decisão

- A raiz é o primeiro diretório, a partir do atual e subindo, com um `pyproject.toml` cujo
  `[project].name` é `praxisforge`. É o mesmo modelo do git com o `.git`.
- `PRAXISFORGE_ROOT` sobrepõe a busca. Precisa ser absoluto e apontar para uma raiz válida; se
  não apontar, a CLI falha em vez de cair na busca.
- Sem raiz encontrada, a CLI sai com código 3 (ambiente) e sugere `PRAXISFORGE_ROOT`.
- `pyproject.toml` ilegível, inválido ou de outro projeto não é raiz e a busca continua.
- Caminhos informados pelo usuário (`sources validate <paths>`, `folders relocate --from`)
  continuam relativos ao diretório atual. Só o padrão do `--from` passou a ser relativo à raiz.
- A busca fica em `infrastructure/project_root.py` e o erro `ProjectRootNotFoundError` no domínio,
  reexportado pela camada de aplicação.

## Alternativas descartadas

- **Relativo ao pacote instalado (`__file__`)**: só funciona com instalação editável a partir do
  clone.
- **`--root` obrigatório fora da raiz**: exige flag em todo comando.

## Consequências

- Todos os comandos funcionam de qualquer subpasta do repositório.
- Fixtures de teste que criam um projeto temporário precisam gravar o `pyproject.toml` marcador.
