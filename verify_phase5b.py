"""Verify Phase 5B print-sheet layout, crop marks, and vector PDF output."""

from __future__ import annotations

import io
import math
import sys
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader

from export.print_sheet import (
    PAGE_MARGIN_MM,
    _append_crop_marks,
    _mark_extension,
    export_print_sheet,
    print_sheet_layout,
)
from export.settings import PrintSheetSettings
from export.csv_loader import load_people
from render import spec_adapter


ROOT = Path(__file__).resolve().parent


def report(label: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'FAIL'}: {label} - {detail}")
    return passed


def main() -> int:
    results: list[bool] = []
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    people, skipped_rows = load_people(ROOT / "sample_data" / "test_250.csv")

    layouts = {}
    for paper in ("A4", "A3"):
        for orientation in ("portrait", "landscape"):
            for bleed in (True, False):
                settings = PrintSheetSettings(orientation=orientation, bleed=bleed)
                layout = print_sheet_layout(paper, settings)
                layouts[(paper, orientation, bleed)] = layout
                width = (
                    layout["columns"] * layout["card_width_mm"]
                    + (layout["columns"] - 1) * layout["gap_mm"]
                    + 2 * _mark_extension(3 if bleed else 0)
                )
                height = (
                    layout["rows"] * layout["card_height_mm"]
                    + (layout["rows"] - 1) * layout["gap_mm"]
                    + 2 * _mark_extension(3 if bleed else 0)
                )
                margins_ok = (
                    width <= layout["page_width_mm"] - 2 * PAGE_MARGIN_MM
                    and height <= layout["page_height_mm"] - 2 * PAGE_MARGIN_MM
                )
                detail = (
                    f"{layout['cards_per_page']} cards/page "
                    f"({layout['columns']} columns x {layout['rows']} rows), "
                    f"gap {layout['gap_mm']:g} mm"
                )
                print(f"{paper} {orientation}, bleed {'on' if bleed else 'off'}: {detail}")
                results.append(report(
                    f"{paper} {orientation} bleed {'on' if bleed else 'off'} geometry and margins",
                    margins_ok and layout["gap_mm"] >= 8,
                    detail,
                ))

    for paper, expected in (("A4", (595.28, 841.89)), ("A3", (841.89, 1190.55))):
        pdf = PdfReader(io.BytesIO(export_print_sheet(
            spec, people[:1], paper, PrintSheetSettings(crop_marks=False),
        )))
        box = pdf.pages[0].mediabox
        actual = (float(box.width), float(box.height))
        results.append(report(
            f"{paper} portrait PDF page size",
            all(abs(value - target) <= 0.02 for value, target in zip(actual, expected)),
            f"{actual[0]:.2f} x {actual[1]:.2f} pt; expected {expected[0]:.2f} x {expected[1]:.2f} pt",
        ))

    landscape_pdf = PdfReader(io.BytesIO(export_print_sheet(
        spec, people[:1], "A4", PrintSheetSettings(orientation="landscape"),
    )))
    landscape_box = landscape_pdf.pages[0].mediabox
    results.append(report(
        "Landscape swaps page dimensions",
        float(landscape_box.width) > float(landscape_box.height),
        f"{float(landscape_box.width):.2f} x {float(landscape_box.height):.2f} pt",
    ))

    mark_svg = ElementTree.Element("{http://www.w3.org/2000/svg}svg")
    _append_crop_marks(mark_svg, 20, 30, 60, 92, 3)
    marks = list(mark_svg)
    crop_ok = len(marks) == 8 and all(
        mark.get("stroke") == "#000000"
        and float(mark.get("stroke-width", "0")) == 0.25
        for mark in marks
    )
    # All four L-shaped corners are composed of two strokes; strokes begin outside bleed.
    crop_ok = crop_ok and all(
        (
            float(mark.get("x1", "0")) < 20
            or float(mark.get("x1", "0")) > 80
            or float(mark.get("y1", "0")) < 30
            or float(mark.get("y1", "0")) > 122
        )
        for mark in marks
    )
    results.append(report("Four crop-mark corners are outside the bleed", crop_ok,
                          f"{len(marks)} black 0.25 mm strokes form four corner marks"))
    gap_layout = print_sheet_layout("A4", PrintSheetSettings())
    nonoverlap = gap_layout["gap_mm"] >= 2 * _mark_extension(3)
    results.append(report("Crop marks do not overlap cards or neighbours", nonoverlap,
                          f"effective gap {gap_layout['gap_mm']:g} mm"))

    started_report: dict[str, object] = {}
    sheet_settings = PrintSheetSettings()
    sheet_pdf_bytes = export_print_sheet(
        spec,
        people,
        "A4",
        sheet_settings,
        report=started_report,
        skipped_rows=skipped_rows,
    )
    sheet_pdf = PdfReader(io.BytesIO(sheet_pdf_bytes))
    expected_pages = math.ceil(len(people) / layouts[("A4", "portrait", True)]["cards_per_page"])
    results.append(report(
        "246 good CSV cards produce the expected page count",
        len(people) == 246
        and started_report["totals"]["exported"] == 246
        and len(sheet_pdf.pages) == expected_pages
        and started_report["totals"]["pages"] == expected_pages,
        f"{started_report['totals']['exported']} cards, {len(sheet_pdf.pages)} pages; "
        f"expected {expected_pages} pages ({started_report['settings']['cards_per_page']} per page)",
    ))

    first_page = sheet_pdf.pages[0]
    resources = first_page["/Resources"].get_object()
    fonts = resources["/Font"].get_object().values()
    embedded = any(
        any(
            key in font.get_object().get("/FontDescriptor", {}).get_object()
            for key in ("/FontFile", "/FontFile2", "/FontFile3")
        )
        for font in fonts
        if "/FontDescriptor" in font.get_object()
    )
    content = first_page.get_contents().get_data()
    image_dimensions = [
        (int(image.get_object()["/Width"]), int(image.get_object()["/Height"]))
        for image in resources.get("/XObject", {}).get_object().values()
        if image.get_object().get("/Subtype") == "/Image"
    ] if "/XObject" in resources else []
    vectors_ok = embedded and len(content) > 10_000 and all(
        width <= 2000 and height <= 2000 for width, height in image_dimensions
    )
    results.append(report(
        "PDF artwork is vector with embedded fonts",
        vectors_ok,
        f"embedded fonts={embedded}, page vector content={len(content)} bytes, "
        f"image sizes={image_dimensions}",
    ))

    one_card_marked = PdfReader(io.BytesIO(export_print_sheet(
        spec, people[:1], "A4", PrintSheetSettings(),
    )))
    no_marks = PdfReader(io.BytesIO(export_print_sheet(
        spec, people[:1], "A4", PrintSheetSettings(crop_marks=False),
    )))
    marked_content = one_card_marked.pages[0].get_contents().get_data()
    no_marks_content = no_marks.pages[0].get_contents().get_data()
    results.append(report(
        "--no-crop-marks removes marks",
        len(marked_content) > len(no_marks_content),
        f"marked page content {len(marked_content)} bytes; unmarked {len(no_marks_content)} bytes",
    ))

    small_pdf = PdfReader(io.BytesIO(export_print_sheet(
        spec, people[:3], "A4", PrintSheetSettings(),
    )))
    results.append(report("Three people fit on one page", len(small_pdf.pages) == 1,
                          f"{len(small_pdf.pages)} page(s)"))
    if all(results):
        print("Phase 5B verification complete.")
        return 0
    print("Phase 5B verification failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
