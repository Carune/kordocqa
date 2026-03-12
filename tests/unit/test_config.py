from app.core.config import get_settings


def test_settings_load_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "test-kordocqa")
    monkeypatch.setenv("ADMIN_TOKEN", "test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "test-kordocqa"
    assert settings.admin_token == "test-token"
    assert settings.openai_api_key == ""

    get_settings.cache_clear()
