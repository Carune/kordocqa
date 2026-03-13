from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from redis import Redis

from app.core.config import Settings, get_settings
from app.db.repositories import RetrievalRepository
from app.db.session import get_session_factory
from app.schemas.evals import EvalMetrics, EvalPromptSummary, EvalRunRequest, EvalRunResponse
from app.services.embeddings import build_embedding_provider
from app.services.llm import ModelProviderError, ModelProviderUnavailableError, build_llm_provider
from app.services.qa import QAResponseValidationError, QAService
from app.services.reranking import IdentityReranker
from app.services.retrieval import RetrievalService

_NO_EVIDENCE_ANSWER = "\uadfc\uac70 \uc5c6\uc74c"
_METRIC_KEYS = [
    "schema_validation_success_rate",
    "citation_validity_rate",
    "refusal_accuracy",
    "expected_phrase_containment_rate",
    "document_hit_rate",
    "chunk_hit_rate",
]


class EvalDatasetRow(BaseModel):
    id: str
    question: str = Field(min_length=1)
    expected_answer_contains: list[str] = Field(default_factory=list)
    gold_document_ids: list[str] = Field(default_factory=list)
    gold_chunk_ids: list[str] = Field(default_factory=list)
    unanswerable: bool


class EvalService:
    def __init__(
        self,
        *,
        qa_service: QAService,
        settings: Settings,
        redis_client: Redis | None = None,
    ) -> None:
        self.qa_service = qa_service
        self.settings = settings
        self.redis_client = redis_client

    def run(self, request: EvalRunRequest) -> EvalRunResponse:
        dataset_path = Path(request.dataset_path or self.settings.eval_default_dataset_path)
        rows = self._load_dataset(dataset_path)

        baseline = self._evaluate_prompt(
            rows=rows,
            prompt_version=request.baseline_prompt_version,
            top_k=request.top_k,
            lexical_k=request.lexical_k,
            semantic_k=request.semantic_k,
        )
        improved = self._evaluate_prompt(
            rows=rows,
            prompt_version=request.improved_prompt_version,
            top_k=request.top_k,
            lexical_k=request.lexical_k,
            semantic_k=request.semantic_k,
        )

        run_id = uuid.uuid4().hex
        generated_at = datetime.now(UTC).isoformat()
        delta = self._build_delta(baseline=baseline, improved=improved)
        report_path = self._write_report(
            run_id=run_id,
            generated_at=generated_at,
            dataset_path=dataset_path,
            baseline=baseline,
            improved=improved,
            delta=delta,
        )
        self._cache_latest_report(
            run_id=run_id,
            generated_at=generated_at,
            dataset_path=str(dataset_path),
            report_path=report_path,
            baseline=baseline,
            improved=improved,
            delta=delta,
        )

        return EvalRunResponse(
            run_id=run_id,
            generated_at=generated_at,
            dataset_path=str(dataset_path),
            report_path=report_path,
            baseline=baseline,
            improved=improved,
            delta=delta,
        )

    def _load_dataset(self, dataset_path: Path) -> list[EvalDatasetRow]:
        if not dataset_path.exists():
            raise FileNotFoundError(f"Eval dataset not found: {dataset_path}")

        rows: list[EvalDatasetRow] = []
        lines = dataset_path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, start=1):
            cleaned = line.strip()
            if not cleaned:
                continue
            try:
                payload = json.loads(cleaned)
                rows.append(EvalDatasetRow.model_validate(payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValueError(f"Invalid eval dataset row at line {index}.") from exc

        if not rows:
            raise ValueError("Eval dataset is empty.")
        return rows

    def _evaluate_prompt(
        self,
        *,
        rows: list[EvalDatasetRow],
        prompt_version: Literal["v1", "v2"],
        top_k: int,
        lexical_k: int,
        semantic_k: int,
    ) -> EvalPromptSummary:
        total = len(rows)
        answerable_count = sum(1 for row in rows if not row.unanswerable)
        unanswerable_count = total - answerable_count
        schema_success_count = 0
        citation_valid_count = 0
        refusal_correct_count = 0
        expected_phrase_hit_count = 0
        document_hit_count = 0
        document_target_count = 0
        chunk_hit_count = 0
        chunk_target_count = 0

        for row in rows:
            try:
                response = self.qa_service.answer(
                    question=row.question,
                    top_k=top_k,
                    lexical_k=lexical_k,
                    semantic_k=semantic_k,
                    prompt_version=prompt_version,
                )
            except (ModelProviderUnavailableError, ModelProviderError):
                raise
            except QAResponseValidationError:
                continue

            schema_success_count += 1
            if self._is_valid_citation_response(
                answer=response.answer,
                citation_count=len(response.citations),
            ):
                citation_valid_count += 1

            if row.unanswerable:
                if response.answer.strip() == _NO_EVIDENCE_ANSWER:
                    refusal_correct_count += 1
            else:
                if self._matches_expected_phrases(
                    answer=response.answer,
                    expected_phrases=row.expected_answer_contains,
                ):
                    expected_phrase_hit_count += 1

            citation_document_ids = {str(citation.document_id) for citation in response.citations}
            citation_chunk_ids = {str(citation.chunk_id) for citation in response.citations}
            if row.gold_document_ids:
                document_target_count += 1
                if citation_document_ids.intersection(row.gold_document_ids):
                    document_hit_count += 1
            if row.gold_chunk_ids:
                chunk_target_count += 1
                if citation_chunk_ids.intersection(row.gold_chunk_ids):
                    chunk_hit_count += 1

        metrics = EvalMetrics(
            total=total,
            answerable_count=answerable_count,
            unanswerable_count=unanswerable_count,
            schema_validation_success_rate=self._ratio(schema_success_count, total),
            citation_validity_rate=self._ratio(citation_valid_count, total),
            refusal_accuracy=self._ratio(refusal_correct_count, unanswerable_count),
            expected_phrase_containment_rate=self._ratio(
                expected_phrase_hit_count,
                answerable_count,
            ),
            document_hit_rate=self._ratio(document_hit_count, document_target_count),
            chunk_hit_rate=self._ratio(chunk_hit_count, chunk_target_count),
        )
        return EvalPromptSummary(prompt_version=prompt_version, metrics=metrics)

    def _matches_expected_phrases(self, *, answer: str, expected_phrases: list[str]) -> bool:
        if not expected_phrases:
            return answer.strip() != _NO_EVIDENCE_ANSWER
        return all(phrase in answer for phrase in expected_phrases)

    def _is_valid_citation_response(self, *, answer: str, citation_count: int) -> bool:
        if answer.strip() == _NO_EVIDENCE_ANSWER:
            return citation_count == 0
        return citation_count > 0

    def _ratio(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 1.0
        return round(numerator / denominator, 4)

    def _build_delta(
        self,
        *,
        baseline: EvalPromptSummary,
        improved: EvalPromptSummary,
    ) -> dict[str, float]:
        baseline_metrics = baseline.metrics.model_dump()
        improved_metrics = improved.metrics.model_dump()
        return {
            key: round(float(improved_metrics[key]) - float(baseline_metrics[key]), 4)
            for key in _METRIC_KEYS
        }

    def _write_report(
        self,
        *,
        run_id: str,
        generated_at: str,
        dataset_path: Path,
        baseline: EvalPromptSummary,
        improved: EvalPromptSummary,
        delta: dict[str, float],
    ) -> str:
        reports_dir = Path(self.settings.eval_reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        output_path = reports_dir / f"eval_report_{run_id}.json"
        payload = {
            "run_id": run_id,
            "generated_at": generated_at,
            "dataset_path": str(dataset_path),
            "baseline": baseline.model_dump(),
            "improved": improved.model_dump(),
            "delta": delta,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(output_path)

    def _cache_latest_report(
        self,
        *,
        run_id: str,
        generated_at: str,
        dataset_path: str,
        report_path: str,
        baseline: EvalPromptSummary,
        improved: EvalPromptSummary,
        delta: dict[str, float],
    ) -> None:
        if self.redis_client is None or self.settings.eval_cache_ttl_seconds <= 0:
            return

        key = f"{self.settings.eval_cache_prefix}:latest_report"
        payload = json.dumps(
            {
                "run_id": run_id,
                "generated_at": generated_at,
                "dataset_path": dataset_path,
                "report_path": report_path,
                "baseline": baseline.model_dump(),
                "improved": improved.model_dump(),
                "delta": delta,
            },
            ensure_ascii=False,
        )
        try:
            self.redis_client.setex(key, self.settings.eval_cache_ttl_seconds, payload)
        except Exception:  # noqa: BLE001
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="Run eval report for kordocqa.")
    parser.add_argument("--dataset", dest="dataset_path", default=None)
    parser.add_argument(
        "--baseline",
        dest="baseline_prompt_version",
        choices=["v1", "v2"],
        default="v1",
    )
    parser.add_argument(
        "--improved",
        dest="improved_prompt_version",
        choices=["v1", "v2"],
        default="v2",
    )
    parser.add_argument("--top-k", dest="top_k", type=int, default=5)
    parser.add_argument("--lexical-k", dest="lexical_k", type=int, default=20)
    parser.add_argument("--semantic-k", dest="semantic_k", type=int, default=20)
    args = parser.parse_args()

    settings = get_settings()
    session_factory = get_session_factory()
    db = session_factory()
    try:
        retrieval_service = RetrievalService(
            repository=RetrievalRepository(db),
            embedding_provider=build_embedding_provider(settings),
            reranker=IdentityReranker(),
            trigram_threshold=settings.retrieval_trigram_threshold,
            index_batch_size=settings.embedding_index_batch_size,
            auto_index_max_chunks=settings.embedding_auto_index_max_chunks,
        )
        qa_service = QAService(
            retrieval_service=retrieval_service,
            llm_provider=build_llm_provider(settings),
            default_top_k=settings.query_top_k,
            default_lexical_k=settings.query_lexical_k,
            default_semantic_k=settings.query_semantic_k,
            default_prompt_version=settings.query_prompt_version,
        )
        try:
            redis_client = Redis.from_url(settings.redis_url)
        except Exception:  # noqa: BLE001
            redis_client = None
        eval_service = EvalService(
            qa_service=qa_service,
            settings=settings,
            redis_client=redis_client,
        )
        result = eval_service.run(
            EvalRunRequest(
                dataset_path=args.dataset_path,
                baseline_prompt_version=args.baseline_prompt_version,
                improved_prompt_version=args.improved_prompt_version,
                top_k=args.top_k,
                lexical_k=args.lexical_k,
                semantic_k=args.semantic_k,
            )
        )
    finally:
        db.close()
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
