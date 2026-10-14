"""Verify Phase 1 card geometry, exports, and logo status."""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image
from pypdf import PdfReader


OUTPUT_DIR = Path(__file__).resolve().parent / "sample_output"
SVG_PATH = OUTPUT_DIR / "card.svg"
PDF_PATH = OUTPUT_DIR / "card.pdf"
PNG_PATH = OUTPUT_DIR / "card.png"
EXPECTED_PDF_WIDTH_PT = 60 / 25.4 * 72
EXPECTED_PDF_HEIGHT_PT = 92 / 25.4 * 72
PDF_TOLERANCE_PT = 0.5


def report(label: str, passed: bool, detail: str) -> bool:
    """Print a PASS/FAIL line and return the result."""
    print(f"{'PASS' if passed else 'FAIL'}: {label} - {detail}")
    return passed


def check_svg() -> tuple[bool, ElementTree.Element | None]:
    """Check the SVG file and exact root geometry."""
    if not SVG_PATH.is_file():
        return report("SVG geometry", False, f"not found: {SVG_PATH}"), None
    try:
        root = ElementTree.parse(SVG_PATH).getroot()
    except (OSError, ElementTree.ParseError) as error:
        return report("SVG geometry", False, f"could not parse SVG: {error}"), None
    passed = (
        root.get("width") == "60mm"
        and root.get("height") == "92mm"
        and root.get("viewBox") == "0 0 60 92"
    )
    detail = f'width={root.get("width")}, height={root.get("height")}, viewBox={root.get("viewBox")}'
    return report("SVG geometry", passed, detail), root


def check_pdf() -> bool:
    """Check for exactly one PDF page at 60 by 92 millimetres."""
    if not PDF_PATH.is_file():
        return report("PDF page size", False, f"not found: {PDF_PATH}")
    try:
        reader = PdfReader(str(PDF_PATH))
        if len(reader.pages) != 1:
            return report("PDF page size", False, f"expected one page, found {len(reader.pages)}")
        box = reader.pages[0].mediabox
        width = float(box.width)
        height = float(box.height)
    except Exception as error:
        return report("PDF page size", False, f"could not read PDF: {error}")
    passed = (
        abs(width - EXPECTED_PDF_WIDTH_PT) <= PDF_TOLERANCE_PT
        and abs(height - EXPECTED_PDF_HEIGHT_PT) <= PDF_TOLERANCE_PT
    )
    return report("PDF page size", passed, f"{width:.2f} x {height:.2f} pt; expected about 170.08 x 260.79 pt")


def check_png() -> bool:
    """Check PNG pixels and its optional 300-DPI metadata."""
    if not PNG_PATH.is_file():
        dimensions_passed = report("PNG dimensions", False, f"not found: {PNG_PATH}")
        dpi_passed = report("PNG DPI metadata", False, "PNG is missing; DPI cannot be checked")
        return dimensions_passed and dpi_passed
    try:
        with Image.open(PNG_PATH) as image:
            width, height = image.size
            dpi = image.info.get("dpi")
    except (OSError, ValueError) as error:
        dimensions_passed = report("PNG dimensions", False, f"could not read PNG: {error}")
        dpi_passed = report("PNG DPI metadata", False, "PNG could not be read")
        return dimensions_passed and dpi_passed

    dimensions_passed = width == 709 and height == 1087
    report("PNG dimensions", dimensions_passed, f"{width} x {height} px; expected 709 x 1087 px")
    if dpi is None:
        dpi_passed = report("PNG DPI metadata", True, "not present; optional check skipped")
    else:
        horizontal_dpi, vertical_dpi = float(dpi[0]), float(dpi[1])
        dpi_passed = abs(horizontal_dpi - 300) <= 2 and abs(vertical_dpi - 300) <= 2
        report("PNG DPI metadata", dpi_passed,
               f"{horizontal_dpi:.1f} x {vertical_dpi:.1f}; expected about 300 DPI")
    return dimensions_passed and dpi_passed


def check_logos(root: ElementTree.Element | None) -> bool:
    """Validate embedded logo data or clearly report each placeholder."""
    if root is None:
        return report("Logo status", False, "cannot inspect logos because the SVG is unavailable")
    details = []
    for name, label in (("acm", "ACM NIT Surat"), ("svnit", "SVNIT")):
        status = root.get(f"data-logo-{name}")
        element = root.find(f".//*[@id='logo-{name}']")
        if status == "embedded" and element is not None:
            href = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")
            if not href or not href.startswith("data:image/") or ";base64," not in href:
                return report("Logo status", False, f"{label} marked embedded without a base64 data URI")
            details.append(f"{label}: embedded")
        elif status == "placeholder" and element is not None:
            text = "".join(element.itertext())
            if f"LOGO MISSING: {name}" not in text:
                return report("Logo status", False, f"{label} placeholder is not clearly labelled")
            details.append(f"{label}: PLACEHOLDER (add assets/{name}.svg or assets/{name}.png)")
        else:
            return report("Logo status", False, f"{label}: missing or inconsistent logo status")
    return report("Logo status", True, "; ".join(details))


def main() -> int:
    """Run each required check and exit nonzero when any check fails."""
    results = []
    svg_passed, root = check_svg()
    results.append(svg_passed)
    results.append(check_pdf())
    results.append(check_png())
    results.append(check_logos(root))
    if all(results):
        print("Phase 1 verification complete.")
        return 0
    print("Phase 1 verification failed. Fix failed items and run again.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())