from fastapi.testclient import TestClient

from app.api.deps import get_runtime_settings
from app.core.config import Settings
from app.main import app


def test_health_dependencies_reports_provider_unconfigured() -> None:
    app.dependency_overrides[get_runtime_settings] = lambda: Settings(
        openai_api_key=None,
        database_url="postgresql+psycopg://user:pass@127.0.0.1:59999/db",
        redis_url="redis://127.0.0.1:63999/0",
    )
    client = TestClient(app)

    response = client.get("/health/dependencies")

    assert response.status_code == 200
    payload = response.json()
    assert "dependencies" in payload
    assert payload["dependencies"]["model_provider"]["status"] == "unconfigured"

    app.dependency_overrides.clear()
