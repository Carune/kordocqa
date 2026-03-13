# kordocqa

Production-lean Korean document RAG QA backend (API-first).

Current status: **M0 + M1 + M2 + M3 implemented** from [`PLANS.md`](./PLANS.md).  
QA generation is intentionally deferred to M4+.

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

## Implemented in M2

- Parser interface + adapters:
  - PDF (`pypdf`)
  - DOCX (OOXML parser)
  - TXT
  - HTML
- Deterministic text normalization + chunking service
- Admin upload endpoint:
  - `POST /api/v1/admin/documents/upload`
- Document/chunk persistence via ingestion service
- Basic ingestion tests (parser/chunking/upload flow)

## Implemented in M3

- Embedding provider adapter with graceful fallback when provider is unconfigured
- Hybrid retrieval service:
  - semantic retrieval (pgvector)
  - lexical retrieval (FTS + trigram fallback)
  - RRF score fusion
- Baseline reranker interface + identity reranker
- Retrieval API:
  - `POST /api/v1/retrieve`
- Retrieval tests (service + API smoke)

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
- Scanned PDFs requiring OCR are out of MVP scope.
- Reindex behavior is deferred; upload ingestion flow is the only implemented admin ingest action.
- Retrieval can fall back to lexical-only mode when model provider is unavailable/unconfigured.
