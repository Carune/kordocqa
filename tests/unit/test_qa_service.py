from __future__ import annotations

import json
import uuid

from app.db.repositories.retrieval import RetrievalCandidate
from app.services.qa import QAService
from app.services.retrieval import RetrievalResult

NO_EVIDENCE = "\uadfc\uac70 \uc5c6\uc74c"


class FakeRetrievalService:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result

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
        return self.result


class FakeLLMProvider:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.called = False

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> str:
        _ = system_prompt
        _ = user_prompt
        self.called = True
        return self.payload


def _candidate() -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="policy evidence content",
        title="policy title",
        section_path="A > B",
        page_number=1,
        metadata={"source": "test"},
        source_filename="policy.txt",
        lexical_score=0.8,
    )


def test_qa_service_builds_answer_with_citations() -> None:
    candidate = _candidate()
    retrieval_result = RetrievalResult(
        status="ok",
        retrieval_mode="lexical_only",
        chunks=[candidate],
    )
    llm_payload = json.dumps(
        {
            "answer": "Policy applies.",
            "citations": [
                {
                    "chunk_id": str(candidate.chunk_id),
                    "quote": "policy evidence content",
                }
            ],
            "confidence": "high",
            "needs_human_review": False,
        },
        ensure_ascii=False,
    )
    service = QAService(
        retrieval_service=FakeRetrievalService(retrieval_result),
        llm_provider=FakeLLMProvider(llm_payload),  # type: ignore[arg-type]
    )

    response = service.answer(question="Does policy apply?")

    assert response.answer == "Policy applies."
    assert response.confidence == "high"
    assert response.needs_human_review is False
    assert len(response.citations) == 1
    assert response.citations[0].chunk_id == candidate.chunk_id
    assert response.citations[0].source_filename == "policy.txt"


def test_qa_service_returns_fallback_when_no_evidence() -> None:
    retrieval_result = RetrievalResult(status="degraded", retrieval_mode="lexical_only", chunks=[])
    fake_provider = FakeLLMProvider(
        payload='{"answer":"x","citations":[],"confidence":"low","needs_human_review":true}'
    )
    service = QAService(
        retrieval_service=FakeRetrievalService(retrieval_result),
        llm_provider=fake_provider,  # type: ignore[arg-type]
    )

    response = service.answer(question="Is there evidence?")

    assert response.answer == NO_EVIDENCE
    assert response.confidence == "low"
    assert response.needs_human_review is True
    assert response.citations == []
    assert fake_provider.called is False


def test_qa_service_returns_fallback_when_citation_id_not_in_retrieved_chunks() -> None:
    candidate = _candidate()
    retrieval_result = RetrievalResult(
        status="ok",
        retrieval_mode="lexical_only",
        chunks=[candidate],
    )
    llm_payload = json.dumps(
        {
            "answer": "Policy applies.",
            "citations": [
                {
                    "chunk_id": str(uuid.uuid4()),
                    "quote": "unknown",
                }
            ],
            "confidence": "medium",
            "needs_human_review": True,
        }
    )
    service = QAService(
        retrieval_service=FakeRetrievalService(retrieval_result),
        llm_provider=FakeLLMProvider(llm_payload),  # type: ignore[arg-type]
    )

    response = service.answer(question="Does policy apply?")

    assert response.answer == NO_EVIDENCE
    assert response.confidence == "low"
    assert response.needs_human_review is True
    assert response.citations == []
