from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_retrieval_service
from app.schemas.retrieval import RetrieveChunk, RetrieveRequest, RetrieveResponse
from app.services.retrieval import RetrievalService

router = APIRouter(prefix="/api/v1", tags=["retrieve"])


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(
    request: RetrieveRequest,
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> RetrieveResponse:
    try:
        result = retrieval_service.retrieve(
            query=request.query,
            top_k=request.top_k,
            lexical_k=request.lexical_k,
            semantic_k=request.semantic_k,
            document_id=request.document_id,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document chunks.",
        ) from exc

    return RetrieveResponse(
        status="ok" if result.status == "ok" else "degraded",
        retrieval_mode="hybrid" if result.retrieval_mode == "hybrid" else "lexical_only",
        chunks=[
            RetrieveChunk(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                score=float(candidate.fusion_score or 0.0),
                lexical_score=candidate.lexical_score,
                semantic_score=candidate.semantic_score,
                content=candidate.content,
                title=candidate.title,
                section_path=candidate.section_path,
                page_number=candidate.page_number,
                metadata=candidate.metadata,
            )
            for candidate in result.chunks
        ],
    )
