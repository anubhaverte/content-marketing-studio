"""Tests for export settings, card formats, people loading, and batch reports."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PIL import Image
from pypdf import PdfReader

from export.batch import export_batch, export_batch_pdf
from export.csv_loader import load_people
from export.exporters import export_card
from export.settings import ExportSettings
from render import spec_adapter


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def card_inputs():
    """Load one spec and person for format-level export checks."""
    return spec_adapter.load_design_spec(), spec_adapter.load_people()[1]


@pytest.mark.parametrize(
    "values",
    [
        {"format": "jpg"},
        {"dpi": 0},
        {"dpi": True},
        {"orientation": "sideways"},
        {"bleed": 1},
    ],
)
def test_settings_reject_invalid_values(values):
    """Reject unsupported output options."""
    with pytest.raises(ValueError):
        ExportSettings(**values)


def test_settings_round_trip_dict():
    """Serialize and restore API-friendly settings."""
    settings = ExportSettings("pdf", 150, "landscape", False)
    assert ExportSettings.from_dict(settings.to_dict()) == settings


@pytest.mark.parametrize(
    ("dpi", "bleed", "expected"),
    [(300, True, (709, 1087)), (300, False, (638, 1016)), (150, True, (354, 543))],
)
def test_png_physical_size(card_inputs, dpi, bleed, expected):
    """Raster output dimensions follow the selected physical size and DPI."""
    spec, person = card_inputs
    result = export_card(spec, person, ExportSettings("png", dpi, bleed=bleed))
    with Image.open(io.BytesIO(result)) as image:
        assert image.size == expected


def test_svg_and_pdf_remain_vector_and_pdf_has_embedded_fonts(card_inputs):
    """SVG retains vector elements and CairoSVG emits a vector PDF with fonts."""
    spec, person = card_inputs
    svg = export_card(spec, person, ExportSettings("svg")).decode("utf-8")
    assert "<text" in svg
    assert "<rect" in svg
    assert "<circle" in svg
    pdf = PdfReader(io.BytesIO(export_card(spec, person, ExportSettings("pdf"))))
    assert len(pdf.pages) == 1
    width, height = float(pdf.pages[0].mediabox.width), float(pdf.pages[0].mediabox.height)
    assert width == pytest.approx(60 / 25.4 * 72, abs=0.5)
    assert height == pytest.approx(92 / 25.4 * 72, abs=0.5)
    fonts = pdf.pages[0]["/Resources"]["/Font"].get_object().values()
    assert any(
        any(key in font.get_object()["/FontDescriptor"].get_object() for key in ("/FontFile", "/FontFile2", "/FontFile3"))
        for font in fonts
        if "/FontDescriptor" in font.get_object()
    )


def test_trim_and_landscape_viewport(card_inputs):
    """Trim crops to the 54x86 mm box and landscape swaps physical dimensions."""
    spec, person = card_inputs
    trimmed = ElementTree.fromstring(
        export_card(spec, person, ExportSettings("svg", bleed=False))
    )
    assert (trimmed.get("width"), trimmed.get("height"), trimmed.get("viewBox")) == (
        "54mm", "86mm", "3 3 54 86",
    )
    landscape = PdfReader(io.BytesIO(
        export_card(spec, person, ExportSettings("pdf", orientation="landscape"))
    ))
    assert float(landscape.pages[0].mediabox.width) > float(landscape.pages[0].mediabox.height)


def test_csv_loader_reports_missing_name_role_id_and_duplicate(tmp_path):
    """Report all malformed CSV lines with physical line numbers."""
    path = tmp_path / "people.csv"
    rows = [
        {"ID": "A", "Name": "Name", "Role": "participant", "Photo": ""},
        {"ID": "B", "Name": "", "Role": "mentor", "Photo": ""},
        {"ID": "C", "Name": "No role", "Role": "not-a-role", "Photo": ""},
        {"ID": "", "Name": "No ID", "Role": "organizer", "Photo": ""},
        {"ID": "A", "Name": "Duplicate", "Role": "volunteer", "Photo": ""},
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=("ID", "Name", "Role", "Photo"))
        writer.writeheader()
        writer.writerows(rows)
    people, problems = load_people(path)
    assert [spec_adapter.person_id(person) for person in people] == ["A"]
    assert [problem["row"] for problem in problems] == [3, 4, 5, 6]
    assert "missing name" in problems[0]["reason"]
    assert "unknown role" in problems[1]["reason"]
    assert "missing id" in problems[2]["reason"]
    assert "duplicate id" in problems[3]["reason"]


def test_json_loader_returns_valid_records_and_problems(tmp_path):
    """Accept JSON arrays while skipping invalid entries."""
    path = tmp_path / "people.json"
    path.write_text(json.dumps([
        {"id": "A", "name": "Name", "role": "participant"},
        {"id": "B", "name": "", "role": "mentor"},
    ]), encoding="utf-8")
    people, problems = load_people(path)
    assert len(people) == 1
    assert problems == [{"row": 2, "reason": "missing name"}]


def test_batch_zip_uses_ids_and_records_skips_and_qa(card_inputs, tmp_path):
    """Package person exports and validation problems into the report."""
    spec, person = card_inputs
    problem = {"row": 5, "reason": "missing name"}
    archive_bytes = export_batch(
        spec, [person], ExportSettings("svg"), skipped_rows=[problem]
    )
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        assert len(names) == 2
        assert any(name.startswith("person-002-participant.") for name in names)
        assert "report.json" in names
        report = json.loads(archive.read("report.json"))
        assert report["totals"]["exported"] == 1
        assert report["skipped_rows"] == [problem]
        assert isinstance(report["people"][0]["qa_issues"], list)
    destination = tmp_path / "out" / "batch.zip"
    export_batch(spec, [person], ExportSettings("svg"), destination)
    assert destination.is_file()


def test_batch_pdf_has_one_page_per_person(card_inputs):
    """Combine multiple card pages without rasterizing them."""
    spec, person = card_inputs
    result = PdfReader(io.BytesIO(
        export_batch_pdf(spec, [person, person], ExportSettings("pdf"))
    ))
    assert len(result.pages) == 2


def test_generator_produces_250_rows():
    """The checked-in generator output has its requested number of rows."""
    rows, problems = load_people(ROOT / "sample_data" / "test_250.csv")
    assert len(rows) == 246
    assert len(problems) == 4
