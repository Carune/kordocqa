# AGENTS.md

## Project goal
Build a production-style Korean document QA backend using FastAPI, Postgres/pgvector, and Redis.
This project is API-first. Do not build a frontend unless explicitly requested.

## Engineering rules
- Use Python 3.12.
- Use FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic.
- Prefer simple, typed Python over heavy abstractions.
- Avoid LangChain/LlamaIndex unless there is a very clear reason. Prefer raw SDKs and small adapters.
- Keep code modular: `app/api`, `app/core`, `app/db`, `app/models`, `app/schemas`, `app/services`, `app/prompts`, `app/evals`, `tests`.
- Every public function should have type hints.
- Add tests for critical logic.
- Document assumptions in `PLANS.md` and `README.md`.
- Use Docker Compose for local development.
- Use environment variables and provide `.env.example`.
- Provide graceful fallbacks when API keys are missing.
- Use `ruff` and `pytest`.
- Return structured JSON for LLM outputs.
- Do not block on minor ambiguities. Choose sensible defaults and document them.
- Before finishing, run lint/tests and fix failures.