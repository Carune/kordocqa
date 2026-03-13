from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_eval_service, get_runtime_settings
from app.core.config import Settings
from app.main import app
from app.schemas.evals import EvalMetrics, EvalPromptSummary, EvalRunResponse


class FakeEvalService:
    def run(self, request) -> EvalRunResponse:  # noqa: ANN001
        _ = request
        metrics = EvalMetrics(
            total=2,
            answerable_count=1,
            unanswerable_count=1,
            schema_validation_success_rate=1.0,
            citation_validity_rate=1.0,
            refusal_accuracy=1.0,
            expected_phrase_containment_rate=1.0,
            document_hit_rate=1.0,
            chunk_hit_rate=1.0,
        )
        return EvalRunResponse(
            run_id="run-1",
            generated_at="2026-03-13T00:00:00+00:00",
            dataset_path="app/evals/datasets/ko_sample_eval.jsonl",
            report_path="app/evals/reports/eval_report_run-1.json",
            baseline=EvalPromptSummary(prompt_version="v1", metrics=metrics),
            improved=EvalPromptSummary(prompt_version="v2", metrics=metrics),
            delta={},
        )


def test_evals_run_endpoint_requires_admin_and_returns_report() -> None:
    app.dependency_overrides[get_runtime_settings] = lambda: Settings(
        admin_token="secret-token",
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
    )
    app.dependency_overrides[get_eval_service] = lambda: FakeEvalService()
    client = TestClient(app)

    missing = client.post("/api/v1/evals/run", json={})
    assert missing.status_code == 401

    response = client.post(
        "/api/v1/evals/run",
        headers={"X-Admin-Token": "secret-token"},
        json={},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-1"
    assert payload["baseline"]["prompt_version"] == "v1"
    assert payload["improved"]["prompt_version"] == "v2"

    app.dependency_overrides.clear()
