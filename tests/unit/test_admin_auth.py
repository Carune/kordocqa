from fastapi.testclient import TestClient

from app.api.deps import get_runtime_settings
from app.core.config import Settings
from app.main import app


def test_admin_token_required_and_validated() -> None:
    app.dependency_overrides[get_runtime_settings] = lambda: Settings(
        admin_token="secret-token",
        database_url="postgresql+psycopg://user:pass@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
    )
    client = TestClient(app)

    missing = client.get("/api/v1/admin/ping")
    assert missing.status_code == 401

    invalid = client.get("/api/v1/admin/ping", headers={"X-Admin-Token": "wrong"})
    assert invalid.status_code == 403

    valid = client.get("/api/v1/admin/ping", headers={"X-Admin-Token": "secret-token"})
    assert valid.status_code == 200
    assert valid.json() == {"status": "ok"}

    app.dependency_overrides.clear()
