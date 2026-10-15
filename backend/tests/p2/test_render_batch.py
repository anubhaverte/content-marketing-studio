"""Tests for POST /render/batch endpoint.

Owned by Person 2 per docs/OWNERS.json.
"""
from __future__ import annotations

import base64
import io
import json
import zipfile
from pypdf import PdfReader
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.brief.schema import Brief
from app.generator.drafts import generate_drafts
from app.spec.schema import Person

client = TestClient(app)


@pytest.fixture
def sample_spec():
    """Return a valid DesignSpec for testing."""
    drafts, _ = generate_drafts(Brief(style_hint="clean"), count=1)
    return drafts[0]


@pytest.fixture
def sample_people() -> list[Person]:
    """Return a list of sample attendees with various roles and missing photos."""
    return [
        Person(
            name="Alice Smith",
            role="participant",
            extra={"id": "P001", "team": "Alpha", "email": "alice@example.com"},
        ),
        Person(
            name="Bob Jones",
            role="organizer",
            extra={"id": "O002", "team": "Core", "email": "bob@example.com"},
        ),
        Person(
            name="Carol Danvers",
            role="mentor",
            extra={"id": "M003", "team": "Mentors", "email": "carol@example.com"},
        ),
    ]


def test_render_batch_stub_when_no_payload():
    """POST /render/batch returns 501 when invoked without payload (legacy stub compatibility)."""
    response = client.post("/render/batch")
    assert response.status_code == 501
    assert "Not implemented yet" in response.json()["detail"]


def test_render_batch_zip_multi_person_success(sample_spec, sample_people):
    """POST /render/batch returns a ZIP archive containing individual PDFs and report.json."""
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people],
        "format": "pdf",
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["X-Total-Count"] == "3"
    assert response.headers["X-Exported-Count"] == "3"
    assert response.headers["X-Failed-Count"] == "0"

    # Verify ZIP contents
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "report.json" in names
        report = json.loads(archive.read("report.json").decode("utf-8"))
        assert report["totals"]["people"] == 3
        assert report["totals"]["exported"] == 3
        assert report["totals"]["failed"] == 0

        # Each person should have an exported PDF file
        pdf_files = [n for n in names if n.endswith(".pdf")]
        assert len(pdf_files) == 3
        assert any("P001" in n for n in pdf_files)
        assert any("O002" in n for n in pdf_files)
        assert any("M003" in n for n in pdf_files)


def test_render_batch_zip_svg_and_png_formats(sample_spec, sample_people):
    """POST /render/batch supports SVG and PNG individual card exports in the ZIP."""
    # Test SVG
    svg_payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people[:2]],
        "format": "svg",
    }
    svg_resp = client.post("/render/batch", json=svg_payload)
    assert svg_resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(svg_resp.content)) as archive:
        svg_files = [n for n in archive.namelist() if n.endswith(".svg")]
        assert len(svg_files) == 2

    # Test PNG
    png_payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people[:1]],
        "format": "png",
        "settings": {"format": "png", "dpi": 150},
    }
    png_resp = client.post("/render/batch", json=png_payload)
    assert png_resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(png_resp.content)) as archive:
        png_files = [n for n in archive.namelist() if n.endswith(".png")]
        assert len(png_files) == 1


def test_render_batch_collated_pdf(sample_spec, sample_people):
    """POST /render/batch collates multiple cards into a single multi-page PDF."""
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people],
        "format": "pdf",
        "collate_pdf": True,
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "cards.pdf" in response.headers["content-disposition"]
    assert response.headers["X-Total-Count"] == "3"

    # Verify PDF page count equals number of attendees
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) == 3


def test_render_batch_missing_photo_initials_fallback(sample_spec):
    """POST /render/batch smoothly renders cards with initials when photos are missing."""
    people_no_photos = [
        Person(name="Dev Without Photo", role="volunteer", extra={"id": "V01"}),
        Person(name="Elena Rostova", role="participant", extra={"id": "P02"}),
    ]
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in people_no_photos],
        "format": "pdf",
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        report = json.loads(archive.read("report.json").decode("utf-8"))
        assert report["totals"]["exported"] == 2


def test_render_batch_with_skipped_rows(sample_spec, sample_people):
    """POST /render/batch preserves skipped rows from CSV validation in report.json."""
    skipped = [{"row": 5, "reason": "missing name"}, {"row": 9, "reason": "invalid role"}]
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people[:2]],
        "skipped_rows": skipped,
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        report = json.loads(archive.read("report.json").decode("utf-8"))
        assert report["totals"]["skipped_rows"] == 2
        assert report["skipped_rows"] == skipped


def test_render_batch_return_json(sample_spec, sample_people):
    """POST /render/batch returns structured JSON report with base64 archive when return_json=True."""
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people[:2]],
        "return_json": True,
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "totals" in data
    assert data["totals"]["people"] == 2
    assert data["totals"]["exported"] == 2
    assert "archive_base64" in data
    assert data["filename"] == "cards.zip"

    # Decode and verify base64 archive
    archive_bytes = base64.b64decode(data["archive_base64"])
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert "report.json" in archive.namelist()


def test_render_batch_collated_pdf_return_json(sample_spec, sample_people):
    """POST /render/batch return_json=True also works for collated PDF."""
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people[:2]],
        "collate_pdf": True,
        "return_json": True,
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "cards.pdf"
    assert data["media_type"] == "application/pdf"
    pdf_bytes = base64.b64decode(data["archive_base64"])
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 2


def test_render_batch_empty_people_returns_400(sample_spec):
    """POST /render/batch returns 400 when people list is empty."""
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [],
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_render_batch_exceeding_max_limit_returns_400(sample_spec):
    """POST /render/batch returns 400 when attendee count exceeds bound."""
    excessive_people = [
        Person(name=f"Person {i}", role="participant").model_dump()
        for i in range(501)
    ]
    payload = {
        "spec": sample_spec.model_dump(),
        "people": excessive_people,
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"].lower()


def test_render_batch_invalid_layout_returns_422(sample_spec, sample_people):
    """POST /render/batch returns 422 when specified layout does not exist."""
    spec_dict = sample_spec.model_dump()
    spec_dict["layout_name"] = "non_existent_layout"
    payload = {
        "spec": spec_dict,
        "people": [p.model_dump() for p in sample_people],
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 422
    assert "cannot be loaded" in response.json()["detail"]


def test_render_batch_collate_pdf_with_non_pdf_returns_400(sample_spec, sample_people):
    """POST /render/batch returns 400 when collate_pdf is requested with non-PDF format."""
    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people],
        "format": "png",
        "collate_pdf": True,
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 400
    assert "collation is only supported for pdf" in response.json()["detail"].lower()


def test_render_batch_partial_failure_handling(sample_spec, sample_people, monkeypatch):
    """POST /render/batch gracefully handles partial failures and reports them accurately."""
    import export.batch

    original_export_card = export.batch.export_card

    def mock_export_card(spec, person, settings, **kwargs):
        if person._data.get("name") == "Bob Jones":
            raise RuntimeError("Simulated export failure for Bob")
        return original_export_card(spec, person, settings, **kwargs)

    monkeypatch.setattr(export.batch, "export_card", mock_export_card)

    payload = {
        "spec": sample_spec.model_dump(),
        "people": [p.model_dump() for p in sample_people],
        "format": "pdf",
    }
    response = client.post("/render/batch", json=payload)
    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "3"
    assert response.headers["X-Exported-Count"] == "2"
    assert response.headers["X-Failed-Count"] == "1"

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        pdf_files = [n for n in names if n.endswith(".pdf")]
        assert len(pdf_files) == 2
        assert "report.json" in names
        report = json.loads(archive.read("report.json").decode("utf-8"))
        assert report["totals"]["people"] == 3
        assert report["totals"]["exported"] == 2
        assert report["totals"]["failed"] == 1
        bob_record = next(r for r in report["people"] if r.get("id") == "O002")
        assert bob_record["status"] == "failed"
        assert "Simulated export failure" in bob_record["reason"]

