from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ingestion_service, get_runtime_settings, require_admin_token
from app.core.config import Settings
from app.schemas.admin import AdminUploadResponse
from app.services.ingestion import IngestionService
from app.services.parsers.base import ParsingError, UnsupportedFormatError

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".html", ".htm"}


@router.get("/ping", dependencies=[Depends(require_admin_token)])
def admin_ping() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/documents/upload",
    response_model=AdminUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_token)],
)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    settings: Annotated[Settings, Depends(get_runtime_settings)],
    db: Annotated[Session, Depends(get_db)],
    ingestion_service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> AdminUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    extension = Path(file.filename).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {extension or '<none>'}",
        )

    payload = await file.read()
    if len(payload) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max_upload_size_bytes={settings.max_upload_size_bytes}.",
        )

    try:
        result = ingestion_service.ingest_upload(
            db=db,
            source_filename=file.filename,
            mime_type=file.content_type,
            payload=payload,
        )
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist uploaded document.",
        ) from exc

    return AdminUploadResponse(
        document_id=result.document_id,
        source_filename=result.source_filename,
        mime_type=result.mime_type,
        status=result.status,
        checksum=result.checksum,
        chunk_count=result.chunk_count,
        title=result.title,
    )
