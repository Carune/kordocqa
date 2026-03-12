# PLANS.md

## 1) Objective

Build a production-lean, API-first Korean document RAG QA backend for internal policies, FAQ, terms, and manuals.

Core capabilities:
- ingest documents (PDF, DOCX, TXT, HTML)
- parse and segment them into metadata-rich chunks
- index chunks in Postgres with pgvector and lexical search support
- retrieve relevant evidence with hybrid retrieval
- generate grounded answers with citations and structured JSON output
- provide evaluation tooling for retrieval and answer quality
- expose clean admin and query APIs
- include operational basics such as logging, health checks, Docker Compose, and CI

This project is intended as a portfolio-grade backend + applied AI system for Korean companies.

## 2) Non-Goals for Initial Release

The initial release will **not** include:
- frontend UI
- multi-tenant support
- OCR-heavy scanned PDF support
- heavy orchestration frameworks such as LangChain or LlamaIndex
- distributed workers or complex job scheduling
- advanced reranker training or fine-tuning

These may be added later, but they are intentionally out of scope for the first implementation.

## 3) Engineering Defaults and Constraints

- Language/runtime: Python 3.12
- API framework: FastAPI
- Persistence: Postgres + pgvector
- Cache/future job queue: Redis
- ORM/migrations: SQLAlchemy 2.x + Alembic
- Testing: pytest
- Linting/formatting: ruff
- Local environment: Docker Compose
- Project config entry point: `pyproject.toml`
- Prefer raw SDK integrations and small adapters over heavyweight abstractions
- Use typed Python and explicit boundaries between layers
- Keep the architecture understandable and production-lean
- Support Korean text well, including mixed Korean/English documents
- Missing model provider API keys must not crash app startup
- Model-backed routes may return explicit provider-unavailable errors when keys are missing
- Admin and eval routes should use a simple `X-Admin-Token` header in the MVP

## 4) High-Level Architecture

```text
[Client]
   |
   v
[FastAPI API Layer]
   |-- /health
   |-- /api/v1/query
   |-- /api/v1/retrieve
   |-- /api/v1/admin/documents/*
   |-- /api/v1/evals/run
   |
   v
[Service Layer]
   |-- ParserService
   |-- ChunkingService
   |-- IndexingService
   |-- RetrievalService
   |-- QAService
   |-- EvalService
   |
   +--> [Postgres + pgvector]
   +--> [Redis]
   +--> [LLM / Embedding Provider Adapter]
   +--> [Tracing Adapter (Langfuse-compatible, no-op by default)]
```

Design principles:
- API-first backend
- deterministic preprocessing where possible
- simple service interfaces
- structured JSON output for generated answers
- clear separation of ingestion, retrieval, QA, and eval responsibilities

## 5) Repository Layout

```text
.
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   ├── router.py
│   │   └── v1/
│   │       ├── admin.py
│   │       ├── query.py
│   │       ├── retrieve.py
│   │       ├── evals.py
│   │       └── health.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── tracing.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── repositories/
│   ├── models/
│   │   ├── document.py
│   │   ├── document_chunk.py
│   │   ├── ingest_job.py
│   │   └── qa_event.py
│   ├── schemas/
│   │   ├── admin.py
│   │   ├── query.py
│   │   ├── retrieval.py
│   │   ├── evals.py
│   │   └── common.py
│   ├── services/
│   │   ├── parsers/
│   │   │   ├── base.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   ├── txt_parser.py
│   │   │   └── html_parser.py
│   │   ├── chunking.py
│   │   ├── ingestion.py
│   │   ├── embeddings.py
│   │   ├── retrieval.py
│   │   ├── reranking.py
│   │   ├── qa.py
│   │   └── evals.py
│   ├── prompts/
│   │   ├── query_answer_v1.txt
│   │   ├── query_answer_v2.txt
│   │   └── answer_schema.json
│   ├── evals/
│   │   ├── datasets/
│   │   └── reports/
│   └── main.py
├── alembic/
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
├── sample_data/
│   └── documents/
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── README.md
└── PLANS.md
```

Repository layout rules:
- keep evaluation code under `app/evals/` and `services/evals.py` only
- avoid duplicate eval directories with overlapping responsibility
- keep prompt templates versioned and explicit

## 6) Implementation Phases

### M0: Scaffold

Deliverables:
- `pyproject.toml`
- FastAPI app skeleton
- `docker-compose.yml`
- `.env.example`
- `Makefile`
- `README.md` stub
- Alembic initialization
- `GET /health`

Out of scope:
- retrieval
- LLM answering
- document ingestion

### M1: Foundation

Deliverables:
- typed settings in `app/core/config.py`
- logging/tracing stubs
- SQLAlchemy session/base setup
- initial Alembic migration
- `documents` and `document_chunks` models
- basic admin auth dependency (`X-Admin-Token`)
- health/dependency checks

Out of scope:
- parser implementations
- embeddings
- retrieval
- answer generation

### M2: Ingestion

Deliverables:
- parsers for PDF, DOCX, TXT, HTML
- deterministic normalization and chunking
- metadata propagation
- upload endpoint
- document persistence
- reindex endpoint skeleton
- tests for parser/chunking/upload flow

Out of scope:
- hybrid retrieval
- LLM answer generation

### M3: Retrieval

Deliverables:
- embedding provider adapter
- vector storage in pgvector
- lexical retrieval in Postgres
- hybrid retrieval with rank fusion
- retrieval-only API endpoint
- baseline reranker interface

Out of scope:
- final query answer generation

### M4: QA

Deliverables:
- grounded answer generation from retrieved evidence only
- structured JSON output validation
- citation construction
- no-answer fallback (`근거 없음`)
- `POST /api/v1/query`
- prompt versioning (v1, v2)

Out of scope:
- advanced human review workflows
- async workers

### M5: Evals and Hardening

Deliverables:
- Korean eval dataset
- eval runner
- baseline vs improved prompt comparison
- request logging improvements
- optional Redis usage for rate-limiting/cache/job hints
- `POST /api/v1/evals/run`
- CI pipeline for lint + tests

## 7) Data Model

### 7.1 `documents`

Purpose:
- store uploaded document metadata and indexing lifecycle

Fields:
- `id` (UUID, PK)
- `source_filename` (text, not null)
- `title` (text, nullable)
- `mime_type` (text, not null)
- `checksum` (text, not null)
- `status` (enum: uploaded, indexed, failed)
- `version` (int, default 1)
- `metadata` (jsonb, nullable)
- `created_at` (timestamptz)
- `updated_at` (timestamptz)

Indexes:
- unique (`checksum`, `version`)
- btree (`status`)

Delete policy:
- MVP uses hard delete
- deleting a document cascades deletes to associated chunks and ingest jobs
- audit/history can be added later if needed

### 7.2 `document_chunks`

Purpose:
- store parsed and chunked document units for retrieval and citation

Fields:
- `id` (UUID, PK)
- `document_id` (UUID, FK -> documents.id, cascade delete)
- `chunk_index` (int, not null)
- `content` (text, not null)
- `title` (text, nullable)
- `section_path` (text, nullable)
- `page_number` (int, nullable)
- `metadata` (jsonb, nullable)
- `content_tsv` (tsvector, indexed for lexical search)
- `embedding` (vector, dimension configured per deployment; default 1536)
- `created_at` (timestamptz)

Indexes:
- unique (`document_id`, `chunk_index`)
- gin (`content_tsv`)
- pgvector index on `embedding`

Notes:
- embedding dimension must be configurable in settings before migration generation
- MVP assumes a single embedding dimension per deployment

### 7.3 `ingest_jobs`

Purpose:
- track ingestion/reindex lifecycle for observability and retries

Fields:
- `id` (UUID, PK)
- `document_id` (UUID, FK)
- `status` (enum: queued, running, success, failed)
- `error_message` (text, nullable)
- `created_at` (timestamptz)
- `started_at` (timestamptz, nullable)
- `finished_at` (timestamptz, nullable)

### 7.4 `qa_events`

Purpose:
- trace query behavior and enable eval sampling/debugging

Fields:
- `id` (UUID, PK)
- `question` (text, not null)
- `answer_json` (jsonb, not null)
- `retrieved_chunk_ids` (uuid[], not null)
- `latency_ms` (int, nullable)
- `created_at` (timestamptz)

## 8) Document Ingestion Strategy

Upload flow:
- client uploads supported file
- API validates file size and extension/MIME
- parser adapter extracts normalized text + structural metadata
- chunking service produces section-aware chunks
- checksum is computed
- document metadata is saved
- indexing is triggered
- document status is updated

Supported formats:
- PDF
- DOCX
- TXT
- HTML

Common parser output contract:
- title
- sections or flattened text blocks
- page_number where available
- source_filename
- raw extracted text

Initial behavior:
- ingestion can be synchronous in early phases
- Redis-backed async execution is optional later
- scanned PDFs without extractable text are treated as unsupported in MVP

## 9) Chunking Strategy

Primary goal:
- preserve Korean document structure and citation quality

Rules:
- prefer heading-aware segmentation
- preserve section titles / heading chains in `section_path`
- use deterministic chunking
- fallback to fixed-size chunking when headings are unavailable
- use modest overlap only when needed
- propagate document/chunk metadata cleanly

Initial defaults:
- heading-aware split first
- fallback chunk size around 500-800 characters
- small overlap for continuity
- page number carried when source parser provides it

## 10) Retrieval Strategy

### 10.1 Semantic Retrieval

- generate embeddings for chunks
- store vectors in pgvector
- retrieve candidates by cosine similarity

### 10.2 Lexical Retrieval

- use Postgres full-text search over `content_tsv`
- for Korean lexical weakness, allow a secondary `pg_trgm`-style similarity fallback if needed
- lexical retrieval should consider:
  - content
  - title
  - section path where useful

### 10.3 Hybrid Retrieval

Combine semantic and lexical candidates using Reciprocal Rank Fusion (RRF).

Default formula:

`rrf_score = sum(1 / (k + rank_i))`

initial `k = 60`

### 10.4 Reranker

Keep reranking minimal in MVP.

Interface:

`rerank(query, candidates) -> candidates`

MVP implementation:
- identity reranker
- or lightweight token-overlap reranker

Advanced model-based reranking is a later enhancement.

## 11) QA Generation Strategy

### 11.1 Query Pipeline

- receive user question
- run retrieval
- prepare evidence bundle
- call answer generation with strict grounding prompt
- validate output schema
- return answer + citations + confidence

### 11.2 Output Contract

```json
{
  "answer": "string",
  "citations": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "source_filename": "string",
      "title": "string",
      "section_path": "string",
      "page_number": 3,
      "quote": "string"
    }
  ],
  "confidence": "high",
  "needs_human_review": false
}
```

Allowed confidence values:
- high
- medium
- low

Grounding rules:
- answer only from retrieved evidence
- do not invent facts outside retrieved context
- citations must reference retrieved chunk IDs only
- if evidence is insufficient or contradictory:
  - `answer`: `"근거 없음"`
  - `confidence`: `"low"`
  - `needs_human_review`: `true`

### 11.3 Prompt Strategy

Use versioned prompt files:
- `app/prompts/query_answer_v1.txt`
- `app/prompts/query_answer_v2.txt`
- `app/prompts/answer_schema.json`

Prompt v1:
- basic grounded QA with citation instructions

Prompt v2:
- stricter refusal behavior
- contradiction handling
- Korean answer style guidance
- explicit JSON-only output emphasis

## 12) API Design

### 12.1 System Endpoints

- `GET /health`
  - liveness check
- `GET /health/dependencies`
  - readiness check for db / redis / model provider availability

### 12.2 Admin Endpoints

All admin endpoints require `X-Admin-Token`.

- `POST /api/v1/admin/documents/upload`
  - multipart file upload
  - persists document metadata
  - triggers parsing/indexing flow
- `POST /api/v1/admin/documents/{document_id}/reindex`
  - reprocesses a document
  - can support forced reindex later
- `GET /api/v1/admin/documents/{document_id}`
  - returns status and metadata
- `DELETE /api/v1/admin/documents/{document_id}`
  - hard deletes document and cascades associated rows

### 12.3 Retrieval / Query Endpoints

- `POST /api/v1/retrieve`
  - retrieval-only debug endpoint
  - useful for evaluating candidate quality before generation
- `POST /api/v1/query`
  - main grounded question-answering endpoint
  - returns structured JSON answer with citations

### 12.4 Eval Endpoint

- `POST /api/v1/evals/run`
  - executes eval runner on configured dataset
  - compares prompt versions where applicable

## 13) Evaluation Strategy

### 13.1 Dataset Format

Store a small Korean eval dataset in JSONL under:

`app/evals/datasets/`

Each row should include:
- id
- question
- expected_document_ids
- expected_chunk_ids (optional)
- expected_answer_contains
- unanswerable

### 13.2 Metrics

Retrieval metrics:
- Recall@K
- MRR
- document hit rate
- chunk hit rate

Answer metrics:
- citation validity rate
- support rate
- refusal accuracy for unanswerable questions
- expected phrase containment
- schema validation success rate

### 13.3 Report Output

Eval reports should be written to:

`app/evals/reports/`

Reports should include:
- baseline prompt vs improved prompt summary
- per-question diff where possible
- aggregate retrieval and answer metrics

## 14) Observability and Error Handling

Logging:
- structured logs only
- include request ID / correlation ID
- include document ID or query event ID when relevant

Suggested fields:
- event
- route
- latency_ms
- document_id
- qa_event_id
- error_type

Tracing:
- tracing interface should be no-op by default
- optional Langfuse-compatible adapter can be enabled later

Error handling:
- invalid file type -> 400
- missing admin token -> 401/403
- provider unavailable -> 503
- schema validation failure -> 500 with structured error
- unsupported scanned PDF -> explicit 422 or domain-specific error

## 15) Security and Input Guardrails

MVP-level controls:
- `X-Admin-Token` for admin and eval routes
- file size limit
- MIME/extension allowlist
- question length limit
- safe timeout/retry defaults for external provider calls
- do not log raw secrets or full provider responses

## 16) Risks and Mitigations

Risk 1: Korean lexical retrieval quality is weaker than English FTS

Mitigation:
- hybrid retrieval by default
- allow trigram-based fallback
- validate with Korean eval dataset rather than assuming quality

Risk 2: Scanned or low-quality PDFs fail extraction

Mitigation:
- treat OCR as explicitly unsupported in MVP
- return clear error status
- document OCR as future work

Risk 3: Hallucination in answer generation

Mitigation:
- strict grounding prompt
- structured JSON schema validation
- refusal fallback (`근거 없음`)
- citation validation against retrieved chunk IDs

Risk 4: Embedding dimension mismatch

Mitigation:
- keep embedding dimension configurable in settings
- document single-dimension-per-deployment assumption
- ensure migration/schema matches configured provider

Risk 5: External provider downtime

Mitigation:
- explicit provider availability checks
- timeouts and retries
- degrade gracefully for model-backed endpoints

## 17) Verification Commands

Local development:

```bash
docker compose up -d
alembic upgrade head
pytest -q
ruff check .
uvicorn app.main:app --reload
```

Eval command target:

```bash
python -m app.services.evals --dataset app/evals/datasets/ko_sample_eval.jsonl
```

If Makefile is added, preferred aliases:
- `make lint`
- `make test`
- `make run`
- `make migrate`

## 18) Exact Next Implementation Steps

Immediate next step:

Implement M1 only. Do not jump to retrieval or QA yet.

M1 checklist:
- create `pyproject.toml`
- implement `app/core/config.py` with typed settings
- implement structured logging and tracing stub
- initialize SQLAlchemy base/session
- initialize Alembic
- implement `documents` and `document_chunks` models
- add `GET /health` and `GET /health/dependencies`
- add admin auth dependency using `X-Admin-Token`
- create Dockerfile, docker-compose, `.env.example`, Makefile
- add basic tests for config loading, app boot, and health endpoints

After M1:

Implement M2 only:
- parser base interface
- PDF/DOCX/TXT/HTML parser adapters
- deterministic normalization and chunking
- upload endpoint
- document persistence
- ingestion tests

After M2:

Implement M3:
- embedding provider adapter
- vector indexing
- lexical retrieval
- RRF fusion
- retrieval API

After M3:

Implement M4:
- grounded QA prompt v1/v2
- answer schema validation
- citation assembly
- `/api/v1/query`

After M4:

Implement M5:
- eval dataset
- eval runner
- prompt comparison report
- CI hardening
