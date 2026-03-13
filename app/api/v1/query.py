from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_qa_service
from app.schemas.query import QueryRequest, QueryResponse
from app.services.llm import ModelProviderError, ModelProviderUnavailableError
from app.services.qa import QAResponseValidationError, QAService

router = APIRouter(prefix="/api/v1", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    qa_service: Annotated[QAService, Depends(get_qa_service)],
) -> QueryResponse:
    try:
        return qa_service.answer(
            question=request.question,
            top_k=request.top_k,
            lexical_k=request.lexical_k,
            semantic_k=request.semantic_k,
            prompt_version=request.prompt_version,
            document_id=request.document_id,
        )
    except ModelProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model provider is unconfigured.",
        ) from exc
    except ModelProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model provider is unavailable.",
        ) from exc
    except QAResponseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"QA output validation failed: {exc}",
        ) from exc

