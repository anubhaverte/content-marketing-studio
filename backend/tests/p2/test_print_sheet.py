"""Tests for print sheet imposition (A4/A3, crop marks, multi-page).

Owned by Person 2 per docs/OWNERS.json.
"""
from __future__ import annotations

import io
from pathlib import Path
import pytest
from pypdf import PdfReader

from app.export.print_sheet import make_print_sheet


SAMPLE_CARD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="60mm" height="92mm" viewBox="0 0 60 92">
  <rect width="60" height="92" fill="#1F6FEB"/>
  <rect x="3" y="3" width="54" height="86" fill="#FFFFFF"/>
  <text x="30" y="50" font-size="6" text-anchor="middle" fill="#0B1220">SAMPLE CARD</text>
</svg>"""


def test_make_print_sheet_a4_single_page(tmp_path: Path):
    """Verify 4 cards on A4 creates a valid 1-page PDF with correct header."""
    out_file = tmp_path / "sheet_a4_single.pdf"
    cards = [SAMPLE_CARD_SVG] * 4

    result_path = make_print_sheet(cards, out_file, page="A4", crop_marks=True)
    assert result_path == out_file
    assert out_file.is_file()
    assert out_file.stat().st_size > 500

    # Verify PDF content and page count using pypdf
    reader = PdfReader(str(out_file))
    assert len(reader.pages) == 1
    # A4 dimensions in points: 210mm = ~595.27pt, 297mm = ~841.89pt
    page = reader.pages[0]
    width_pt = float(page.mediabox.width)
    height_pt = float(page.mediabox.height)
    assert 590 <= width_pt <= 600
    assert 835 <= height_pt <= 848


def test_make_print_sheet_a4_multipage(tmp_path: Path):
    """Verify 11 cards on A4 creates a 2-page PDF (9 per page)."""
    out_file = tmp_path / "sheet_a4_multi.pdf"
    cards = [SAMPLE_CARD_SVG] * 11

    make_print_sheet(cards, out_file, page="A4", crop_marks=True)
    assert out_file.is_file()

    reader = PdfReader(str(out_file))
    assert len(reader.pages) == 2


def test_make_print_sheet_a3(tmp_path: Path):
    """Verify A3 sheet dimensions (4x4 = 16 cards capacity)."""
    out_file = tmp_path / "sheet_a3.pdf"
    cards = [SAMPLE_CARD_SVG] * 16

    make_print_sheet(cards, out_file, page="A3", crop_marks=True)
    assert out_file.is_file()

    reader = PdfReader(str(out_file))
    assert len(reader.pages) == 1
    # A3 dimensions in points: 297mm = ~841.89pt, 420mm = ~1190.55pt
    page = reader.pages[0]
    width_pt = float(page.mediabox.width)
    height_pt = float(page.mediabox.height)
    assert 835 <= width_pt <= 848
    assert 1185 <= height_pt <= 1195


def test_make_print_sheet_without_crop_marks(tmp_path: Path):
    """Verify crop_marks=False executes cleanly."""
    out_file = tmp_path / "sheet_no_crops.pdf"
    cards = [SAMPLE_CARD_SVG] * 2

    make_print_sheet(cards, out_file, page="A4", crop_marks=False)
    assert out_file.is_file()
    reader = PdfReader(str(out_file))
    assert len(reader.pages) == 1


def test_make_print_sheet_empty_cards_error(tmp_path: Path):
    """Verify empty card list raises ValueError."""
    out_file = tmp_path / "empty.pdf"
    with pytest.raises(ValueError, match="empty cards list"):
        make_print_sheet([], out_file, page="A4")


def test_make_print_sheet_unsupported_page_error(tmp_path: Path):
    """Verify unsupported page format raises ValueError."""
    out_file = tmp_path / "letter.pdf"
    with pytest.raises(ValueError, match="Unsupported page format"):
        make_print_sheet([SAMPLE_CARD_SVG], out_file, page="Letter")
