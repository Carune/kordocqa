from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    lexical_k: int = Field(default=20, ge=1, le=200)
    semantic_k: int = Field(default=20, ge=1, le=200)
    document_id: uuid.UUID | None = None


class RetrieveChunk(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    score: float
    lexical_score: float | None = None
    semantic_score: float | None = None
    content: str
    title: str | None = None
    section_path: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] | None = None


class RetrieveResponse(BaseModel):
    status: Literal["ok", "degraded"]
    retrieval_mode: Literal["hybrid", "lexical_only"]
    chunks: list[RetrieveChunk]

