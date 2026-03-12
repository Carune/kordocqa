# kordocqa

Production-lean Korean document RAG QA backend (API-first).

Current status: **M0 + M1 implemented** from [`PLANS.md`](./PLANS.md).  
Ingestion, retrieval, and QA generation are intentionally deferred to M2+.

## Tech stack

- Python 3.12
- FastAPI + Pydantic v2
- Postgres (pgvector) + Redis
- SQLAlchemy 2.x + Alembic
- pytest + ruff
- Docker Compose

## Implemented in M0/M1

- FastAPI skeleton with:
  - `GET /health`
  - `GET /health/dependencies`
- Typed settings (`app/core/config.py`)
- Structured logging stub (`app/core/logging.py`)
- Tracing stub (`app/core/tracing.py`)
- SQLAlchemy setup (`app/db/base.py`, `app/db/session.py`)
- Alembic init + initial migration (documents/document_chunks)
- Admin token dependency (`X-Admin-Token`)
- Dockerfile + docker-compose + Makefile + CI

## Quick start

1. Copy environment template:
   ```bash
   cp .env.example .env
   ```
2. Install dependencies:
   ```bash
   python3 -m pip install ".[dev]"
   ```
3. Start dependencies:
   ```bash
   docker compose up -d postgres redis
   ```
4. Run migration:
   ```bash
   make migrate
   ```
5. Run checks:
   ```bash
   make lint
   make test
   ```
6. Run API:
   ```bash
   make run
   ```

## Assumptions

- This project is API-first and backend-only.
- If provider API keys are missing, app startup must still work.
- `/health/dependencies` reports model provider as `unconfigured` when keys are absent.
