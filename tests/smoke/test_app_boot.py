from fastapi import FastAPI

from app.main import create_app


def test_create_app_boots() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)

    route_paths = {route.path for route in app.routes}
    assert "/health" in route_paths
    assert "/health/dependencies" in route_paths
    assert "/api/v1/retrieve" in route_paths
