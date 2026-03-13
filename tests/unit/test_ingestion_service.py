from __future__ import annotations

import uuid

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import ChunkingService
from app.services.ingestion import IngestionService


class FakeSession:
    def __init__(self) -> None:
        self.items: list[object] = []
        self.committed = False
        self.rolled_back = False

    def add(self, item: object) -> None:
        self.items.append(item)

    def flush(self) -> None:
        for item in self.items:
            if isinstance(item, Document) and item.id is None:
                item.id = uuid.uuid4()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_ingestion_service_persists_document_and_chunks() -> None:
    service = IngestionService(
        chunking_service=ChunkingService(chunk_size_chars=80, chunk_overlap_chars=10)
    )
    db = FakeSession()

    result = service.ingest_upload(
        db=db,  # type: ignore[arg-type]
        source_filename="sample.txt",
        mime_type="text/plain",
        payload=("policy clause A " * 100).encode("utf-8"),
    )

    documents = [item for item in db.items if isinstance(item, Document)]
    chunks = [item for item in db.items if isinstance(item, DocumentChunk)]

    assert db.committed is True
    assert db.rolled_back is False
    assert len(documents) == 1
    assert len(chunks) == result.chunk_count
    assert result.status == "indexed"
    assert result.chunk_count > 1

