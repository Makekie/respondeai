APP_FILE = main
APP_INSTANCE = app
PORT = 8000

hello:
	echo "Hello, this is my first make command"

venv:
	uv venv

install: venv
	uv sync

install-dev: venv
	uv sync --group dev

setup: install
	@echo "Projeto configurado com sucesso!"

clean:
	rm -rf .venv

run:
	@echo "🚀 Iniciando aplicação..."
	@if [ ! -d ".venv" ]; then echo "⚠️ Ambiente virtual não encontrado. Execute 'make install' primeiro."; exit 1; fi
	cd src && uv run uvicorn $(APP_FILE):$(APP_INSTANCE) --reload --host 0.0.0.0 --port $(PORT)

test_service:
	cd src && python3 tests/test_services.py

# Extração de documentos
extract-docs:
	@echo "Uso: make extract-docs PASTA=/caminho/para/pdfs"
	@if [ -z "$(PASTA)" ]; then echo "❌ Especifique PASTA=/caminho/para/pdfs"; exit 1; fi
	cd src && uv run python extract_documents.py "$(PASTA)"

extract-docs-all:
	@echo "Uso: make extract-docs-all PASTA=/caminho/para/pdfs (inclui vetados)"
	@if [ -z "$(PASTA)" ]; then echo "❌ Especifique PASTA=/caminho/para/pdfs"; exit 1; fi
	cd src && uv run python extract_documents.py "$(PASTA)" --incluir-vetados