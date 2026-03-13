PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

.PHONY: install lint test eval run up down migrate migrate-down

install:
	$(PIP) install ".[dev]"

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest

eval:
	$(PYTHON) -m app.services.evals --dataset app/evals/datasets/ko_sample_eval.jsonl

run:
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	$(PYTHON) -m alembic upgrade head

migrate-down:
	$(PYTHON) -m alembic downgrade -1

up:
	docker compose up -d

down:
	docker compose down
