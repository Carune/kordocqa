from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.api.deps import get_db, get_runtime_settings
from app.core.config import Settings
from app.main import app
from app.models.document import Document


class FakeSession:
    def __init__(self) -> None:
        self.items: list[object] = []

    def add(self, item: object) -> None:
        self.items.append(item)

    def flush(self) -> None:
        for item in self.items:
            if isinstance(item, Document) and item.id is None:
                item.id = uuid.uuid4()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_admin_upload_txt() -> None:
    session = FakeSession()
    app.dependency_overrides[get_runtime_settings] = lambda: Settings(
        admin_token="secret-token",
        max_upload_size_bytes=1024 * 1024,
        chunk_size_chars=120,
        chunk_overlap_chars=10,
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
    )
    app.dependency_overrides[get_db] = lambda: session

    client = TestClient(app)
    response = client.post(
        "/api/v1/admin/documents/upload",
        headers={"X-Admin-Token": "secret-token"},
        files={"file": ("sample.txt", "upload test sentence " * 20, "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "indexed"
    assert payload["chunk_count"] >= 1
    assert payload["source_filename"] == "sample.txt"

    app.dependency_overrides.clear()


def test_admin_upload_rejects_unsupported_extension() -> None:
    app.dependency_overrides[get_runtime_settings] = lambda: Settings(
        admin_token="secret-token",
        max_upload_size_bytes=1024 * 1024,
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
    )
    app.dependency_overrides[get_db] = lambda: FakeSession()

    client = TestClient(app)
    response = client.post(
        "/api/v1/admin/documents/upload",
        headers={"X-Admin-Token": "secret-token"},
        files={"file": ("sample.exe", "binary", "application/octet-stream")},
    )

    assert response.status_code == 400

    app.dependency_overrides.clear()

