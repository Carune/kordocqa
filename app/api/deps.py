from __future__ import annotations

import secrets
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


def get_runtime_settings() -> Settings:
    return get_settings()


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
