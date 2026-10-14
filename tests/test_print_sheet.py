"""Tests for vector print-sheet layout and crop marks."""

from __future__ import annotations

import io
from xml.etree import ElementTree

import pytest
from pypdf import PdfReader

from export import print_sheet
from export.print_sheet import export_print_sheet, print_sheet_layout
from export.settings import PrintSheetSettings
from qa.checks import Issue
from render import spec_adapter
from render.text_fit import find_font_file, measure_text


ROOT = spec_adapter.PROJECT_ROOT


@pytest.mark.parametrize(
    ("paper", "orientation", "bleed", "expected"),
    [
        ("A4", "portrait", True, 4),
        ("A4", "landscape", True, 4),
        ("A3", "portrait", True, 12),
        ("A3", "landscape", True, 10),
        ("A4", "portrait", False, 4),
        ("A4", "landscape", False, 4),
        ("A3", "portrait", False, 12),
        ("A3", "landscape", False, 10),
    ],
)
def test_cards_per_page_match_geometry(paper, orientation, bleed, expected):
    layout = print_sheet_layout(
        paper,
        PrintSheetSettings(orientation=orientation, bleed=bleed),
    )
    assert layout["cards_per_page"] == expected
    assert layout["gap_mm"] >= 8
    required_width = (
        layout["columns"] * layout["card_width_mm"]
        + (layout["columns"] - 1) * layout["gap_mm"]
        + (2 * print_sheet._mark_extension(3 if bleed else 0))
    )
    required_height = (
        layout["rows"] * layout["card_height_mm"]
        + (layout["rows"] - 1) * layout["gap_mm"]
        + (2 * print_sheet._mark_extension(3 if bleed else 0))
    )
    assert required_width <= layout["page_width_mm"] - 20
    assert required_height <= layout["page_height_mm"] - 20


@pytest.mark.parametrize(
    ("paper", "expected"),
    [("A4", (595.28, 841.89)), ("A3", (841.89, 1190.55))],
)
def test_pdf_page_size_fonts_and_vectors(paper, expected):
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    people = spec_adapter.load_people()[:3]
    result = PdfReader(io.BytesIO(export_print_sheet(
        spec, people, paper, PrintSheetSettings(crop_marks=False),
    )))
    assert len(result.pages) == 1
    page = result.pages[0]
    assert float(page.mediabox.width) == pytest.approx(expected[0], abs=0.02)
    assert float(page.mediabox.height) == pytest.approx(expected[1], abs=0.02)
    fonts = page["/Resources"]["/Font"].get_object().values()
    assert any(
        any(
            key in font.get_object().get("/FontDescriptor", {}).get_object()
            for key in ("/FontFile", "/FontFile2", "/FontFile3")
        )
        for font in fonts
        if "/FontDescriptor" in font.get_object()
    )
    assert len(page.get_contents().get_data()) > 8_000


def test_landscape_and_multipage_pdf():
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    people = spec_adapter.load_people()
    portrait = print_sheet_layout("A4", PrintSheetSettings())
    landscape_settings = PrintSheetSettings(orientation="landscape", crop_marks=False)
    landscape = PdfReader(io.BytesIO(export_print_sheet(spec, people[:3], "A4", landscape_settings)))
    assert float(landscape.pages[0].mediabox.width) > float(landscape.pages[0].mediabox.height)
    report: dict[str, object] = {}
    pdf = export_print_sheet(
        spec,
        people[:portrait["cards_per_page"] + 1],
        "A4",
        PrintSheetSettings(crop_marks=False),
        report=report,
    )
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 2
    assert report["totals"]["pages"] == 2


@pytest.mark.parametrize(
    ("card_width", "card_height", "bleed"),
    [(60, 92, 3), (54, 86, 0)],
)
def test_crop_marks_are_four_outside_trim_and_bleed(card_width, card_height, bleed):
    root = ElementTree.Element(f"{{{print_sheet.SVG_NS}}}svg")
    x, y = 20, 30
    print_sheet._append_crop_marks(root, x, y, card_width, card_height, bleed)
    marks = list(root)
    assert len(marks) == 8
    assert all(mark.get("stroke") == "#000000" for mark in marks)
    assert all(float(mark.get("stroke-width")) == pytest.approx(0.25) for mark in marks)
    trim_left, trim_top = x + bleed, y + bleed
    trim_right, trim_bottom = trim_left + card_width - 2 * bleed, trim_top + card_height - 2 * bleed
    corners = set()
    for mark in marks:
        x1, y1, x2, y2 = (float(mark.get(key)) for key in ("x1", "y1", "x2", "y2"))
        assert (x1 == x2) != (y1 == y2)
        if x1 == x2:
            assert x1 in {trim_left, trim_right}
            row = "top" if max(y1, y2) < trim_top else "bottom"
            column = "left" if x1 == trim_left else "right"
        else:
            assert y1 in {trim_top, trim_bottom}
            row = "top" if y1 == trim_top else "bottom"
            column = "left" if max(x1, x2) < trim_left else "right"
        corners.add((column, row))
        assert max(x1, x2) <= x or min(x1, x2) >= x + card_width or (
            max(y1, y2) <= y or min(y1, y2) >= y + card_height
        )
    assert corners == {
        ("left", "top"),
        ("right", "top"),
        ("left", "bottom"),
        ("right", "bottom"),
    }


def test_no_crop_marks_removes_vector_strokes():
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    person = spec_adapter.load_people()[0]
    with_marks = export_print_sheet(spec, [person], "A4", PrintSheetSettings())
    without_marks = export_print_sheet(
        spec, [person], "A4", PrintSheetSettings(crop_marks=False),
    )
    assert len(with_marks) > len(without_marks)


def test_event_name_page_label_is_present_and_long_names_fit():
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    long_name = "Very long event name " * 30
    page_root = ElementTree.Element(f"{{{print_sheet.SVG_NS}}}svg")
    print_sheet._append_page_label(page_root, 210, 297, 1, long_name)
    label = page_root[-1]
    font_family, font_path = find_font_file(["Arial", "Segoe UI"])
    assert label.text == long_name
    assert label.get("font-family") == font_family
    assert measure_text(long_name, font_path, float(label.get("font-size")[:-2])) <= 180

    labeled_spec = spec_adapter.DesignSpec({
        **spec._data,
        "event": {"name": "Community Summit"},
    })
    pdf = PdfReader(io.BytesIO(export_print_sheet(
        labeled_spec,
        spec_adapter.load_people()[:1],
        "A4",
        PrintSheetSettings(crop_marks=False),
    )))
    extracted = pdf.pages[0].extract_text()
    assert "Community Summit" in extracted


def test_qa_errors_are_reported_and_skipped(monkeypatch):
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    person = spec_adapter.load_people()[0]
    monkeypatch.setattr(print_sheet, "render_card", lambda *_args: "<svg/>")
    monkeypatch.setattr(
        print_sheet,
        "run_qa",
        lambda *_args: [Issue("test", "error", "person-001", "bad card")],
    )
    report: dict[str, object] = {}
    pdf = export_print_sheet(spec, [person], "A4", PrintSheetSettings(), report=report)
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 1
    assert report["totals"]["exported"] == 0
    assert report["people"][0]["status"] == "failed"
    assert report["people"][0]["qa_issues"][0]["check"] == "test"
