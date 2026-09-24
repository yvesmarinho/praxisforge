# Makefile — Praxisforge
# Gerado por scaffold.py em 2026-09-18T18:56:11Z

.PHONY: help init dev build test lint format clean validate-data security

## Mostra esta ajuda
help:
	@grep -E '^## ' Makefile | sed 's/## //'

## [DEPRECATED] — use: uv run scripts/scaffold.py
init:
	@echo ""
	@echo " ⚠️  Para criar/configurar o projeto, use diretamente:"
	@echo "      uv run scripts/scaffold.py"
	@echo "      python scripts/scaffold.py"
	@echo ""

## Instala dependências
install-deps:
	@uv sync

## Inicia servidor de desenvolvimento
dev:
	@echo "Iniciando desenvolvimento..."

## Build de produção
build:
	@echo "Buildando..."

## Executa testes
test:
	@uv run pytest

## Lint do código
lint:
	@uv run ruff check . && uv run mypy

## Formata código
format:
	@uv run ruff format src tests

## Remove arquivos gerados
clean:
	@rm -rf dist/ build/ __pycache__/ .pytest_cache/ *.egg-info/ .coverage htmlcov/

## Valida src/data contra os contratos versionados em schemas/
validate-data:
	@uv run yamllint src/data
	@uv run check-jsonschema --schemafile schemas/folders-schema-v2.json src/data/folders.example.yaml
	@if [ -d src/data/sources ]; then uv run praxisforge sources validate src/data/sources; fi

## Roda bandit e safety sobre o código-fonte
security:
	@uv run bandit -r src -q
	@uv run safety check

## Carrega variáveis MCP do .secrets/.env e orienta a abrir o VS Code
mcp:
	@bash scripts/load-mcp.sh