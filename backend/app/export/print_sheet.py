"""Print sheets: several cards per A4/A3 page with gaps and crop marks.

Follows Track 4 non-negotiables:
- Everything in mm.
- Standard ISO/IEC 7810 ID-1 card: finished trim 54 x 86 mm.
- 3mm bleed on all sides -> card canvas 60 x 92 mm.
- Safe area: 4mm inside trim line.
- A4: 210 x 297 mm (3 x 3 = 9 cards per page, 15mm X margin, 10.5mm Y margin).
- A3: 297 x 420 mm (4 x 4 = 16 cards per page, 28.5mm X margin, 26mm Y margin).
- Precise crop marks at card trim corners without cutting into the finished artwork.
"""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter


SHEET_DIMENSIONS: dict[str, tuple[float, float, int, int]] = {
    # format: (sheet_w_mm, sheet_h_mm, cols, rows)
    "A4": (210.0, 297.0, 3, 3),
    "A3": (297.0, 420.0, 4, 4),
}

CARD_W_MM = 60.0
CARD_H_MM = 92.0
BLEED_MM = 3.0
TRIM_W_MM = 54.0
TRIM_H_MM = 86.0


def _extract_svg_inner(card_svg: str, card_idx: int) -> str:
    """Extract inner elements of a card SVG and namespace IDs to prevent collisions."""
    # Prefix IDs to avoid document-wide collisions
    scoped_svg = re.sub(r'\bid="([^"]+)"', rf'id="c{card_idx}_\1"', card_svg)
    scoped_svg = re.sub(r'url\(#([^)]+)\)', rf'url(#c{card_idx}_\1)', scoped_svg)
    scoped_svg = re.sub(r'href="#([^"]+)"', rf'href="#c{card_idx}_\1"', scoped_svg)

    # Extract contents between <svg ...> and </svg>
    match = re.search(r"<svg[^>]*>(.*)</svg>", scoped_svg, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return scoped_svg


def _generate_crop_marks(card_x: float, card_y: float) -> str:
    """Generate SVG paths for print crop marks at the 4 corners of a card's trim box."""
    trim_x1 = card_x + BLEED_MM
    trim_x2 = card_x + BLEED_MM + TRIM_W_MM
    trim_y1 = card_y + BLEED_MM
    trim_y2 = card_y + BLEED_MM + TRIM_H_MM

    mark_len = 2.5
    mark_gap = 0.5
    stroke_w = 0.15

    lines = []
    # Top-Left corner
    lines.append(f'<line x1="{trim_x1 - mark_len - mark_gap:.2f}" y1="{trim_y1:.2f}" x2="{trim_x1 - mark_gap:.2f}" y2="{trim_y1:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')
    lines.append(f'<line x1="{trim_x1:.2f}" y1="{trim_y1 - mark_len - mark_gap:.2f}" x2="{trim_x1:.2f}" y2="{trim_y1 - mark_gap:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')

    # Top-Right corner
    lines.append(f'<line x1="{trim_x2 + mark_gap:.2f}" y1="{trim_y1:.2f}" x2="{trim_x2 + mark_gap + mark_len:.2f}" y2="{trim_y1:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')
    lines.append(f'<line x1="{trim_x2:.2f}" y1="{trim_y1 - mark_len - mark_gap:.2f}" x2="{trim_x2:.2f}" y2="{trim_y1 - mark_gap:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')

    # Bottom-Left corner
    lines.append(f'<line x1="{trim_x1 - mark_len - mark_gap:.2f}" y1="{trim_y2:.2f}" x2="{trim_x1 - mark_gap:.2f}" y2="{trim_y2:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')
    lines.append(f'<line x1="{trim_x1:.2f}" y1="{trim_y2 + mark_gap:.2f}" x2="{trim_x1:.2f}" y2="{trim_y2 + mark_gap + mark_len:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')

    # Bottom-Right corner
    lines.append(f'<line x1="{trim_x2 + mark_gap:.2f}" y1="{trim_y2:.2f}" x2="{trim_x2 + mark_gap + mark_len:.2f}" y2="{trim_y2:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')
    lines.append(f'<line x1="{trim_x2:.2f}" y1="{trim_y2 + mark_gap:.2f}" x2="{trim_x2:.2f}" y2="{trim_y2 + mark_gap + mark_len:.2f}" stroke="#000000" stroke-width="{stroke_w}"/>')

    return "".join(lines)


def _build_page_svg(
    page_cards: list[tuple[int, str]],  # (global_idx, svg)
    page_num: int,
    total_pages: int,
    sheet_w: float,
    sheet_h: float,
    cols: int,
    rows: int,
    paper_name: str,
    crop_marks: bool,
) -> str:
    """Build a complete SVG markup document for one print sheet page."""
    margin_x = (sheet_w - cols * CARD_W_MM) / 2.0
    margin_y = (sheet_h - rows * CARD_H_MM) / 2.0

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{sheet_w:.1f}mm" height="{sheet_h:.1f}mm" viewBox="0 0 {sheet_w:.1f} {sheet_h:.1f}">',
        f'<rect width="{sheet_w:.1f}" height="{sheet_h:.1f}" fill="#FFFFFF"/>',
    ]

    for slot_idx, (global_card_idx, card_svg) in enumerate(page_cards):
        col = slot_idx % cols
        row = slot_idx // cols
        card_x = margin_x + col * CARD_W_MM
        card_y = margin_y + row * CARD_H_MM

        inner_content = _extract_svg_inner(card_svg, global_card_idx)
        # Nest card SVG with explicit coordinate box and viewport
        parts.append(
            f'<svg x="{card_x:.2f}" y="{card_y:.2f}" width="{CARD_W_MM:.2f}" height="{CARD_H_MM:.2f}" '
            f'viewBox="0 0 {CARD_W_MM:.2f} {CARD_H_MM:.2f}">{inner_content}</svg>'
        )

        if crop_marks:
            parts.append(_generate_crop_marks(card_x, card_y))

    # Print slug in bottom margin
    slug_y = sheet_h - 3.5
    parts.append(
        f'<text x="{margin_x:.2f}" y="{slug_y:.2f}" font-family="monospace" font-size="2.4" fill="#666666">'
        f'ACM ID Card Studio • Sheet Page {page_num} of {total_pages} • {paper_name} ({sheet_w:.0f}×{sheet_h:.0f}mm) • '
        f'Bleed: 3mm • Trim: 54×86mm</text>'
    )

    parts.append("</svg>")
    return "".join(parts)


def make_print_sheet(
    card_svgs: list[str],
    out_path: Path,
    page: str = "A4",
    crop_marks: bool = True,
) -> Path:
    """Place cards in an imposition grid on A4/A3 paper and export a print-ready vector PDF.

    Args:
        card_svgs: List of raw SVG strings, each sized 60 x 92 mm with 3mm bleed.
        out_path: Destination path for the resulting .pdf file.
        page: Paper format ('A4' or 'A3').
        crop_marks: Whether to draw crop mark lines at the finished trim boundaries.

    Returns:
        Path to the saved PDF file.
    """
    import cairosvg

    paper_key = page.strip().upper()
    if paper_key not in SHEET_DIMENSIONS:
        valid_keys = ", ".join(SHEET_DIMENSIONS.keys())
        raise ValueError(f"Unsupported page format: {page!r}. Supported formats: {valid_keys}")

    sheet_w, sheet_h, cols, rows = SHEET_DIMENSIONS[paper_key]
    cards_per_page = cols * rows

    if not card_svgs:
        raise ValueError("Cannot create print sheet from empty cards list.")

    # Paginate cards into groups
    total_cards = len(card_svgs)
    total_pages = (total_cards + cards_per_page - 1) // cards_per_page

    page_pdfs: list[bytes] = []

    for page_idx in range(total_pages):
        start = page_idx * cards_per_page
        end = min(start + cards_per_page, total_cards)
        page_card_items = [(idx, card_svgs[idx]) for idx in range(start, end)]

        page_svg = _build_page_svg(
            page_cards=page_card_items,
            page_num=page_idx + 1,
            total_pages=total_pages,
            sheet_w=sheet_w,
            sheet_h=sheet_h,
            cols=cols,
            rows=rows,
            paper_name=paper_key,
            crop_marks=crop_marks,
        )

        pdf_bytes = cairosvg.svg2pdf(bytestring=page_svg.encode("utf-8"))
        page_pdfs.append(pdf_bytes)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if total_pages == 1:
        out_path.write_bytes(page_pdfs[0])
    else:
        writer = PdfWriter()
        for pdf_data in page_pdfs:
            reader = PdfReader(io.BytesIO(pdf_data))
            for page_obj in reader.pages:
                writer.add_page(page_obj)
        with open(out_path, "wb") as f:
            writer.write(f)

    return out_path
