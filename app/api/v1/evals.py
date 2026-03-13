from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_eval_service, require_admin_token
from app.schemas.evals import EvalRunRequest, EvalRunResponse
from app.services.evals import EvalService
from app.services.llm import ModelProviderError, ModelProviderUnavailableError

router = APIRouter(
    prefix="/api/v1/evals",
    tags=["evals"],
    dependencies=[Depends(require_admin_token)],
)


@router.post("/run", response_model=EvalRunResponse)
def run_evals(
    request: EvalRunRequest,
    eval_service: Annotated[EvalService, Depends(get_eval_service)],
) -> EvalRunResponse:
    try:
        return eval_service.run(request)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
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
