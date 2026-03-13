from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, request_logging_middleware
from app.core.tracing import TracingAdapter


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    tracer = TracingAdapter()

    app = FastAPI(
        title=settings.app_name,
        description="Production-lean Korean document RAG QA backend",
        version="0.1.0",
    )
    app.state.tracer = tracer
    app.middleware("http")(request_logging_middleware)

    app.include_router(api_router)

    return app


app = create_app()
