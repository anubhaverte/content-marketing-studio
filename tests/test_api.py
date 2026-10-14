"""Smoke tests for the stable application-facing API."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from pypdf import PdfReader

from export.api import (
    export_batch_zip,
    export_card_bytes,
    export_print_sheet_pdf,
    list_layouts,
    list_themes,
    load_people_file,
    render_card_svg,
    render_preview_svg,
    run_qa_for_card,
)
from render import spec_adapter


ROOT = Path(__file__).resolve().parents[1]


def test_render_and_qa_public_functions_accept_json_objects():
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    person = spec_adapter.load_people()[1]
    spec_data = dict(spec._data)
    person_data = dict(person._data)

    svg = render_card_svg(spec_data, person_data)
    assert isinstance(svg, str)
    assert svg.startswith("<svg")
    assert "Cher" in svg

    preview = render_preview_svg(spec_data, "participant")
    assert isinstance(preview, str)
    assert preview.startswith("<svg")

    issues = run_qa_for_card(spec_data, person_data)
    assert isinstance(issues, list)
    if issues:
        assert {"check", "severity", "person_id", "message"} <= issues[0].keys()


def test_card_batch_and_print_sheet_exports_return_bytes_and_report():
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    person = spec_adapter.load_people()[1]
    spec_data = dict(spec._data)
    person_data = dict(person._data)

    card = export_card_bytes(spec_data, person_data, {"format": "svg"})
    assert isinstance(card, bytes)
    assert b"<svg" in card

    archive_bytes, batch_report = export_batch_zip(
        spec_data,
        [person_data],
        {"format": "svg"},
    )
    assert isinstance(archive_bytes, bytes)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert "report.json" in archive.namelist()
    assert batch_report["totals"]["exported"] == 1
    assert batch_report["people"][0]["status"] == "exported"

    pdf_bytes, sheet_report = export_print_sheet_pdf(
        spec_data,
        [person_data],
        "A4",
        {"crop_marks": False},
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(PdfReader(io.BytesIO(pdf_bytes)).pages) == 1
    assert sheet_report["totals"]["exported"] == 1
    assert sheet_report["totals"]["pages"] == 1


def test_people_file_and_template_list_functions():
    people, problems = load_people_file(ROOT / "sample_data" / "people.json")
    assert len(people) == 8
    assert problems == []
    assert all(isinstance(person, spec_adapter.Person) for person in people)
    assert list_layouts() == ["classic", "split"]
    assert list_themes() == ["blue", "dark"]
