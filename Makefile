UV_CACHE_DIR ?= .uv-cache
UV_PYTHON_INSTALL_DIR ?= .uv-python
export UV_CACHE_DIR UV_PYTHON_INSTALL_DIR

.PHONY: help setup start stop reset snapshot test test-unit lint format format-check clean

help:
	@echo "Available targets: setup, start, stop, reset, snapshot, test, test-unit, lint, format, format-check, clean"

setup:
	uv sync --python 3.12

start:
	docker compose up --build -d

stop:
	docker compose down

reset:
	docker compose run --rm legacy-api flask --app legacy_app:create_app db-reset

snapshot:
	docker compose run --rm legacy-api flask --app legacy_app:create_app db-snapshot

test:
	docker compose run --rm -e TEST_DATABASE_URL=postgresql+psycopg://benchmark:benchmark@db:5432/benchmark legacy-api pytest

test-unit:
	uv run pytest -m "not postgres"

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

clean:
	uv cache clean
