from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.services.chunking import ChunkingService
from app.services.parsers import ParserFactory
from app.services.parsers.base import ParsingError, UnsupportedFormatError


@dataclass(slots=True)
class IngestionResult:
    document_id: uuid.UUID
    source_filename: str
    mime_type: str
    status: str
    checksum: str
    chunk_count: int
    title: str | None


class IngestionService:
    def __init__(
        self,
        parser_factory: ParserFactory | None = None,
        chunking_service: ChunkingService | None = None,
    ) -> None:
        self.parser_factory = parser_factory or ParserFactory()
        self.chunking_service = chunking_service or ChunkingService()

    def ingest_upload(
        self,
        db: Session,
        *,
        source_filename: str,
        mime_type: str | None,
        payload: bytes,
    ) -> IngestionResult:
        if not payload:
            raise ParsingError("Uploaded file is empty.")

        parsed_document = self.parser_factory.parse_document(
            payload=payload,
            source_filename=source_filename,
            mime_type=mime_type,
        )
        chunks = self.chunking_service.build_chunks(parsed_document)
        checksum = hashlib.sha256(payload).hexdigest()
        resolved_mime_type = mime_type or "application/octet-stream"

        try:
            document = Document(
                source_filename=source_filename,
                title=parsed_document.title,
                mime_type=resolved_mime_type,
                checksum=checksum,
                status=DocumentStatus.INDEXED,
                version=1,
                extra_data={
                    "parser_metadata": parsed_document.metadata,
                    "raw_text_length": len(parsed_document.raw_text),
                },
            )
            db.add(document)
            db.flush()

            if document.id is None:
                raise SQLAlchemyError("Document ID was not generated during flush.")

            for chunk_index, chunk in enumerate(chunks):
                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk_index,
                        content=chunk.content,
                        title=chunk.title,
                        section_path=chunk.section_path,
                        page_number=chunk.page_number,
                        extra_data=chunk.metadata,
                    )
                )

            db.commit()
            return IngestionResult(
                document_id=document.id,
                source_filename=document.source_filename,
                mime_type=document.mime_type,
                status=document.status.value,
                checksum=document.checksum,
                chunk_count=len(chunks),
                title=document.title,
            )
        except (ParsingError, UnsupportedFormatError):
            db.rollback()
            raise
        except SQLAlchemyError:
            db.rollback()
            raise

