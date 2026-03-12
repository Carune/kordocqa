from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from redis import Redis

from app.api.deps import get_runtime_settings
from app.core.config import Settings
from app.db.session import check_database
from app.schemas.common import DependencyHealthResponse, DependencyState, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def _check_redis(settings: Settings) -> tuple[str, str]:
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return ("up", "redis reachable")
    except Exception as exc:  # noqa: BLE001
        return ("down", str(exc))


@router.get("/health/dependencies", response_model=DependencyHealthResponse)
def health_dependencies(
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> DependencyHealthResponse:
    db_status, db_detail = check_database(settings)
    redis_status, redis_detail = _check_redis(settings)

    if settings.openai_api_key:
        provider_state = DependencyState(
            status="configured",
            detail=f"{settings.provider_name} api key configured",
        )
    else:
        provider_state = DependencyState(
            status="unconfigured",
            detail=f"{settings.provider_name} api key missing",
        )

    overall = "ok" if db_status == "up" and redis_status == "up" else "degraded"

    return DependencyHealthResponse(
        status=overall,
        dependencies={
            "database": DependencyState(status=db_status, detail=db_detail),
            "redis": DependencyState(status=redis_status, detail=redis_detail),
            "model_provider": provider_state,
        },
    )
