"""Focused tests for the POST /render/preview endpoint."""
import xml.etree.ElementTree as ET
from fastapi.testclient import TestClient

from app.main import app
from app.brief.schema import Brief
from app.generator.drafts import generate_drafts
from app.spec.schema import Person

client = TestClient(app)


def _sample_spec():
    drafts, _ = generate_drafts(Brief(style_hint="clean"), count=1)
    return drafts[0]


def test_render_preview_success():
    spec = _sample_spec()
    person = Person(name="Jane Doe", role="participant", id="PART-001")

    payload = {
        "spec": spec.model_dump(),
        "person": person.model_dump(),
        "debug_guides": False,
    }
    response = client.post("/render/preview", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "svg" in data
    assert "qa_issues" in data
    assert isinstance(data["qa_issues"], list)

    svg = data["svg"]
    root = ET.fromstring(svg)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("width") == "60mm"
    assert root.get("height") == "92mm"
    assert root.get("viewBox") == "0 0 60 92"
    assert "Jane Doe" in svg
    assert "debug-guides" not in svg


def test_render_preview_with_debug_guides():
    spec = _sample_spec()
    person = Person(name="Jane Doe", role="organizer", id="ORG-001")

    payload = {
        "spec": spec.model_dump(),
        "person": person.model_dump(),
        "debug_guides": True,
    }
    response = client.post("/render/preview", json=payload)
    assert response.status_code == 200

    svg = response.json()["svg"]
    assert "debug-guides" in svg
    assert "guide-bleed" in svg
    assert "guide-trim" in svg
    assert "guide-safe" in svg


def test_render_preview_missing_photo_initials_fallback():
    spec = _sample_spec()
    person = Person(name="Avery Sample", role="mentor", photo=None)

    payload = {
        "spec": spec.model_dump(),
        "person": person.model_dump(),
        "debug_guides": False,
    }
    response = client.post("/render/preview", json=payload)
    assert response.status_code == 200

    svg = response.json()["svg"]
    qa_issues = response.json()["qa_issues"]
    assert "data-photo-status=\"fallback\"" in svg
    assert "AS" in svg  # Avery Sample initials

    photo_warnings = [i for i in qa_issues if i["check"] == "empty_fields" and "Photo is missing" in i["message"]]
    assert len(photo_warnings) >= 1


def test_render_preview_all_roles():
    spec = _sample_spec()
    for role in ("participant", "organizer", "mentor", "volunteer"):
        person = Person(name=f"Role Test {role}", role=role, id=f"{role[:3]}-123")
        payload = {
            "spec": spec.model_dump(),
            "person": person.model_dump(),
        }
        response = client.post("/render/preview", json=payload)
        assert response.status_code == 200
        svg = response.json()["svg"]
        assert role.upper() in svg or f"Role Test {role}" in svg


def test_render_preview_invalid_body_422():
    # Empty body
    r1 = client.post("/render/preview", json={})
    assert r1.status_code == 422

    # Missing person
    spec = _sample_spec()
    r2 = client.post("/render/preview", json={"spec": spec.model_dump()})
    assert r2.status_code == 422

    # Extra fields forbidden
    r3 = client.post("/render/preview", json={
        "spec": spec.model_dump(),
        "person": Person(name="Test").model_dump(),
        "unknown_extra": 123,
    })
    assert r3.status_code == 422


def test_render_preview_unknown_layout_422():
    spec = _sample_spec().model_copy(deep=True)
    spec_data = spec.model_dump()
    spec_data["layout_name"] = "nonexistent_layout_xyz"

    payload = {
        "spec": spec_data,
        "person": Person(name="Test User").model_dump(),
    }
    response = client.post("/render/preview", json=payload)
    assert response.status_code == 422
    assert "Layout 'nonexistent_layout_xyz' cannot be loaded" in response.json()["detail"]


def test_render_preview_empty_call_preserves_501():
    # Calling without any body preserves legacy Phase 0 stub test
    response = client.post("/render/preview")
    assert response.status_code == 501


def test_render_batch_remains_stub_501():
    # /render/batch remains stub until Phase 3 batch integration
    response = client.post("/render/batch")
    assert response.status_code == 501
