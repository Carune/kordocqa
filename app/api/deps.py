from __future__ import annotations

import secrets
from collections.abc import Generator
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.services.chunking import ChunkingService
from app.services.ingestion import IngestionService
from app.services.parsers import ParserFactory


def get_runtime_settings() -> Settings:
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_ingestion_service(
    settings: Annotated[Settings, Depends(get_runtime_settings)],
) -> IngestionService:
    return IngestionService(
        parser_factory=ParserFactory(),
        chunking_service=ChunkingService(
            chunk_size_chars=settings.chunk_size_chars,
            chunk_overlap_chars=settings.chunk_overlap_chars,
        ),
    )


def require_admin_token(
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    x_admin_token: Annotated[Optional[str], Header(alias="X-Admin-Token")] = None,
) -> None:
    if not settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token is not configured.",
        )

    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Admin-Token header.",
        )

    if not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token.",
        )
