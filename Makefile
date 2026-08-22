.PHONY: start stop build pre-commit format test

all: start

start:
	docker compose -f src/docker-compose.yml up -d

stop:
	docker compose -f src/docker-compose.yml down

build:
	docker compose -f src/docker-compose.yml up --build -d

pre-commit:
	uv run --dev pre-commit run --all-files

format:
	uv run --dev ruff format .
	uv run --dev ruff check . --fix

test:
	uv run --dev python -m pytest tests/
