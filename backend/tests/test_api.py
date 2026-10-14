"""The API starts and answers."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": "0.0.1"}


def test_render_routes_are_stubs():
    assert client.post("/render/preview").status_code == 501
    assert client.post("/render/batch").status_code == 501
