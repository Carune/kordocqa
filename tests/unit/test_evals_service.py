from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from app.core.config import Settings
from app.schemas.evals import EvalRunRequest
from app.schemas.query import QueryCitation, QueryResponse
from app.services.evals import EvalService

NO_EVIDENCE = "\uadfc\uac70 \uc5c6\uc74c"


class FakeQAService:
    def __init__(self, *, document_id: uuid.UUID, chunk_id: uuid.UUID) -> None:
        self.document_id = document_id
        self.chunk_id = chunk_id

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
        _ = top_k
        _ = lexical_k
        _ = semantic_k
        _ = document_id
        if question == "Q1":
            if prompt_version == "v1":
                return QueryResponse(
                    answer="Policy exists.",
                    citations=[
                        QueryCitation(
                            chunk_id=self.chunk_id,
                            document_id=self.document_id,
                            source_filename="policy.txt",
                            quote="policy evidence",
                        )
                    ],
                    confidence="medium",
                    needs_human_review=False,
                )
            return QueryResponse(
                answer="Policy approved.",
                citations=[
                    QueryCitation(
                        chunk_id=self.chunk_id,
                        document_id=self.document_id,
                        source_filename="policy.txt",
                        quote="policy evidence",
                    )
                ],
                confidence="high",
                needs_human_review=False,
            )

        if prompt_version == "v1":
            return QueryResponse(
                answer="Unknown but likely yes.",
                citations=[
                    QueryCitation(
                        chunk_id=self.chunk_id,
                        document_id=self.document_id,
                        source_filename="policy.txt",
                        quote="guess",
                    )
                ],
                confidence="low",
                needs_human_review=True,
            )
        return QueryResponse(
            answer=NO_EVIDENCE,
            citations=[],
            confidence="low",
            needs_human_review=True,
        )


def _write_dataset(path: Path, *, document_id: uuid.UUID, chunk_id: uuid.UUID) -> None:
    rows = [
        {
            "id": "ko-test-1",
            "question": "Q1",
            "expected_answer_contains": ["approved"],
            "gold_document_ids": [str(document_id)],
            "gold_chunk_ids": [str(chunk_id)],
            "unanswerable": False,
        },
        {
            "id": "ko-test-2",
            "question": "Q2",
            "expected_answer_contains": [],
            "gold_document_ids": [],
            "gold_chunk_ids": [],
            "unanswerable": True,
        },
    ]
    payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    path.write_text(payload, encoding="utf-8")


def test_eval_service_compares_prompt_versions_and_writes_report(tmp_path: Path) -> None:
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    dataset_path = tmp_path / "dataset.jsonl"
    report_dir = tmp_path / "reports"
    _write_dataset(dataset_path, document_id=document_id, chunk_id=chunk_id)

    settings = Settings(
        eval_default_dataset_path=str(dataset_path),
        eval_reports_dir=str(report_dir),
        eval_cache_ttl_seconds=0,
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
    )
    service = EvalService(
        qa_service=FakeQAService(
            document_id=document_id,
            chunk_id=chunk_id,
        ),  # type: ignore[arg-type]
        settings=settings,
    )

    result = service.run(
        EvalRunRequest(
            dataset_path=str(dataset_path),
            baseline_prompt_version="v1",
            improved_prompt_version="v2",
            top_k=3,
            lexical_k=5,
            semantic_k=5,
        )
    )

    assert result.baseline.prompt_version == "v1"
    assert result.improved.prompt_version == "v2"
    assert result.improved.metrics.expected_phrase_containment_rate > (
        result.baseline.metrics.expected_phrase_containment_rate
    )
    assert result.improved.metrics.refusal_accuracy > result.baseline.metrics.refusal_accuracy
    assert Path(result.report_path).exists()
