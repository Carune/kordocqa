from __future__ import annotations

import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response

from app.core.config import Settings

RequestHandler = Callable[[Request], Awaitable[Response]]


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.upper(),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


async def request_logging_middleware(request: Request, call_next: RequestHandler) -> Response:
    logger = get_logger("app.request")
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    route = request.url.path
    method = request.method
    start = time.perf_counter()
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, route=route, method=method)

    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "request_failed",
            status_code=500,
            latency_ms=latency_ms,
        )
        structlog.contextvars.clear_contextvars()
        raise

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    structlog.contextvars.clear_contextvars()
    return response
