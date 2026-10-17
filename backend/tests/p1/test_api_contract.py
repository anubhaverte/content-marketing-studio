"""Tests for the API contract endpoints using FastAPI TestClient."""
import io
import pytest
from fastapi.testclient import TestClient

from app.generator.library import get_layout, get_theme
from app.main import app
from app.spec.loader import merge_design_spec

client = TestClient(app)


def test_health():
    """GET /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_roles():
    """GET /roles returns 200 OK with list of role definitions."""
    response = client.get("/roles")
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    role_ids = {r["id"] for r in roles}
    assert "participant" in role_ids
    assert "organizer" in role_ids


@pytest.mark.parametrize("name", ["layout", "theme", "design_spec", "design-spec", "brief", "person", "patch_op", "patch-op"])
def test_schema_valid(name: str):
    """GET /schema/{name} returns 200 OK with JSON schema dictionary."""
    response = client.get(f"/schema/{name}")
    assert response.status_code == 200
    schema = response.json()
    assert isinstance(schema, dict)
    assert "title" in schema or "properties" in schema or "$schema" in schema


def test_schema_invalid():
    """GET /schema/{invalid} returns 404 Not Found."""
    response = client.get("/schema/nonexistent_schema_type")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_templates_list():
    """GET /templates/layouts and /templates/themes list available templates."""
    res_layouts = client.get("/templates/layouts")
    assert res_layouts.status_code == 200
    layouts = res_layouts.json()
    assert isinstance(layouts, list)
    assert "classic" in layouts

    res_themes = client.get("/templates/themes")
    assert res_themes.status_code == 200
    themes = res_themes.json()
    assert isinstance(themes, list)
    assert "clean_light" in themes


def test_templates_get_valid():
    """GET /templates/layouts/{name} and /themes/{name} return template JSON."""
    res_layout = client.get("/templates/layouts/classic")
    assert res_layout.status_code == 200
    layout_data = res_layout.json()
    assert layout_data["name"] == "classic"

    res_theme = client.get("/templates/themes/clean_light")
    assert res_theme.status_code == 200
    theme_data = res_theme.json()
    assert theme_data["name"] == "clean_light"


def test_templates_get_invalid():
    """GET nonexistent layout or theme returns 404."""
    assert client.get("/templates/layouts/does_not_exist").status_code == 404
    assert client.get("/templates/themes/does_not_exist").status_code == 404


def test_templates_path_traversal():
    """Path traversal attempts are rejected with 404."""
    assert client.get("/templates/layouts/..%2Fmain").status_code == 404
    assert client.get("/templates/themes/..%2Fmain").status_code == 404


def test_spec_patch_success():
    """POST /spec/patch applies ops to a spec and returns updated spec and diff."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")
    spec = merge_design_spec(layout, theme)

    payload = {
        "spec": spec.model_dump(mode="json"),
        "ops": [
            {"op": "set", "path": "theme.colors.primary", "value": "#004488"}
        ],
    }

    response = client.post("/spec/patch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "spec" in data
    assert data["spec"]["theme"]["colors"]["primary"] == "#004488"


def test_spec_patch_invalid():
    """POST /spec/patch returns 422 if an invalid patch operation is requested."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")
    spec = merge_design_spec(layout, theme)

    payload = {
        "spec": spec.model_dump(mode="json"),
        "ops": [
            {"op": "set", "path": "schema_version", "value": "2.0"}
        ],
    }

    response = client.post("/spec/patch", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_brief_mock(monkeypatch):
    """POST /brief returns 200 OK with mock questions."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post("/brief", json={"text": "Hackathon 2026 at SVNIT Surat"})
    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is True
    assert "brief" in data
    assert len(data["questions"]) == 6


def test_data_upload_csv():
    """POST /data/upload parses CSV and returns DataSummary."""
    csv_content = b"Name,Role,Team,Email,ID\nAlice,organizer,Core,alice@nit.edu,ORG01\nBob,participant,Hackers,bob@nit.edu,P01\n"
    files = {"file": ("attendees.csv", io.BytesIO(csv_content), "text/csv")}

    response = client.post("/data/upload", files=files)
    assert response.status_code == 200
    summary = response.json()
    assert summary["mock"] is True
    assert summary["people_loaded"] == 2
    assert "name" in summary["column_mapping"]


def test_data_upload_invalid_extension():
    """POST /data/upload returns 400 for non-CSV files."""
    txt_content = b"Some plain text"
    files = {"file": ("data.txt", io.BytesIO(txt_content), "text/plain")}

    response = client.post("/data/upload", files=files)
    assert response.status_code == 400
    assert "Only .csv files are supported" in response.json()["detail"]


def test_drafts_generation():
    """POST /drafts generates candidate DesignSpecs."""
    req_2 = {
        "brief": {"design_type": "id_card", "event_name": "Test Fest"},
        "count": 2,
    }
    res_2 = client.post("/drafts", json=req_2)
    assert res_2.status_code == 200
    data_2 = res_2.json()
    assert data_2["mock"] is False
    assert len(data_2["drafts"]) == 2

    req_5 = {
        "brief": {"design_type": "id_card", "event_name": "Big Fest"},
        "count": 5,
    }
    res_5 = client.post("/drafts", json=req_5)
    assert res_5.status_code == 200
    data_5 = res_5.json()
    assert len(data_5["drafts"]) == 5

    # Count > 9 is rejected with 422
    req_bad = {
        "brief": {"design_type": "id_card", "event_name": "Too Many"},
        "count": 10,
    }
    res_bad = client.post("/drafts", json=req_bad)
    assert res_bad.status_code == 422


def test_render_preview_stub():
    """POST /render/preview returns 200 with rendered SVG and QA issues."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")
    spec = merge_design_spec(layout, theme)

    payload = {
        "spec": spec.model_dump(mode="json"),
        "person": {"name": "Test User", "role": "participant"},
    }
    response = client.post("/render/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "svg" in data
    assert isinstance(data["svg"], str) and len(data["svg"]) > 0
    assert "<svg" in data["svg"]
    assert "Test User" in data["svg"]
    assert "qa_issues" in data
    assert isinstance(data["qa_issues"], list)

