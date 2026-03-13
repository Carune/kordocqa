from __future__ import annotations

import uuid
from typing import Literal

from fastapi.testclient import TestClient

from app.api.deps import get_qa_service
from app.main import app
from app.schemas.query import QueryCitation, QueryResponse
from app.services.llm import ModelProviderUnavailableError


class FakeQAService:
    def answer(
        self,
        *,
        question: str,
        top_k: int | None = None,
        lexical_k: int | None = None,
        semantic_k: int | None = None,
        prompt_version: Literal["v1", "v2"] | None = None,
        document_id: uuid.UUID | None = None,
    ) -> QueryResponse:
        _ = question
        _ = top_k
        _ = lexical_k
        _ = semantic_k
        _ = prompt_version
        _ = document_id
        return QueryResponse(
            answer="test answer",
            citations=[
                QueryCitation(
                    chunk_id=uuid.uuid4(),
                    document_id=uuid.uuid4(),
                    source_filename="policy.txt",
                    title="policy",
                    section_path="A > B",
                    page_number=1,
                    quote="quoted evidence",
                )
            ],
            confidence="high",
            needs_human_review=False,
        )


class UnavailableQAService:
    def answer(
        self,
        *,
        question: str,
        top_k: int | None = None,
        lexical_k: int | None = None,
        semantic_k: int | None = None,
        prompt_version: Literal["v1", "v2"] | None = None,
        document_id: uuid.UUID | None = None,
    ) -> QueryResponse:
        _ = question
        _ = top_k
        _ = lexical_k
        _ = semantic_k
        _ = prompt_version
        _ = document_id
        raise ModelProviderUnavailableError("not configured")


def test_query_endpoint_returns_structured_answer() -> None:
    app.dependency_overrides[get_qa_service] = lambda: FakeQAService()
    client = TestClient(app)

    response = client.post("/api/v1/query", json={"question": "What is the policy?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "test answer"
    assert body["confidence"] == "high"
    assert body["needs_human_review"] is False
    assert len(body["citations"]) == 1

    app.dependency_overrides.clear()


def test_query_endpoint_returns_503_when_provider_unconfigured() -> None:
    app.dependency_overrides[get_qa_service] = lambda: UnavailableQAService()
    client = TestClient(app)

    response = client.post("/api/v1/query", json={"question": "What is the policy?"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Model provider is unconfigured."

    app.dependency_overrides.clear()
