from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvalRunRequest(BaseModel):
    dataset_path: str | None = None
    baseline_prompt_version: Literal["v1", "v2"] = "v1"
    improved_prompt_version: Literal["v1", "v2"] = "v2"
    top_k: int = Field(default=5, ge=1, le=50)
    lexical_k: int = Field(default=20, ge=1, le=200)
    semantic_k: int = Field(default=20, ge=1, le=200)


class EvalMetrics(BaseModel):
    total: int
    answerable_count: int
    unanswerable_count: int
    schema_validation_success_rate: float
    citation_validity_rate: float
    refusal_accuracy: float
    expected_phrase_containment_rate: float
    document_hit_rate: float
    chunk_hit_rate: float


class EvalPromptSummary(BaseModel):
    prompt_version: Literal["v1", "v2"]
    metrics: EvalMetrics


class EvalRunResponse(BaseModel):
    run_id: str
    generated_at: str
    dataset_path: str
    report_path: str
    baseline: EvalPromptSummary
    improved: EvalPromptSummary
    delta: dict[str, float]
