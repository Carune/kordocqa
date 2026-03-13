from __future__ import annotations

import uuid

from pydantic import BaseModel


class AdminUploadResponse(BaseModel):
    document_id: uuid.UUID
    source_filename: str
    mime_type: str
    status: str
    checksum: str
    chunk_count: int
    title: str | None = None

