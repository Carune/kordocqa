from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.api.deps import get_retrieval_service
from app.db.repositories.retrieval import RetrievalCandidate
from app.main import app
from app.services.retrieval import RetrievalResult


class FakeRetrievalService:
    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        lexical_k: int,
        semantic_k: int,
        document_id: uuid.UUID | None = None,
    ) -> RetrievalResult:
        _ = query
        _ = top_k
        _ = lexical_k
        _ = semantic_k
        _ = document_id
        return RetrievalResult(
            status="ok",
            retrieval_mode="hybrid",
            chunks=[
                RetrievalCandidate(
                    chunk_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    content="sample content",
                    title="sample title",
                    section_path="A > B",
                    page_number=3,
                    metadata={"source": "test"},
                    lexical_score=0.2,
                    semantic_score=0.9,
                )
            ],
        )


def test_retrieve_endpoint_returns_hybrid_results() -> None:
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/retrieve",
        json={"query": "what is policy", "top_k": 3, "lexical_k": 5, "semantic_k": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["retrieval_mode"] == "hybrid"
    assert len(payload["chunks"]) == 1
    assert payload["chunks"][0]["content"] == "sample content"

    app.dependency_overrides.clear()

