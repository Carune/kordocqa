from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    lexical_k: int | None = Field(default=None, ge=1, le=200)
    semantic_k: int | None = Field(default=None, ge=1, le=200)
    prompt_version: Literal["v1", "v2"] | None = None
    document_id: uuid.UUID | None = None


class QueryCitation(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    source_filename: str
    title: str | None = None
    section_path: str | None = None
    page_number: int | None = None
    quote: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[QueryCitation]
    confidence: Literal["high", "medium", "low"]
    needs_human_review: bool

