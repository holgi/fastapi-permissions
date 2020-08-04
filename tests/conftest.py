import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client():
    from fastapi_permissions.example import app

    return TestClient(app)


@pytest.fixture()
def example_app_openapi(client):
    response = client.get("/openapi.json")
    return response.json()
