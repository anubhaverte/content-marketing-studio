"""Verify Phase 5A export settings, outputs, CSV validation, and batch ZIPs."""

from __future__ import annotations

import io
import json
import sys
import time
import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from export.batch import export_batch
from export.csv_loader import load_people
from export.exporters import export_card
from export.settings import ExportSettings
from render import spec_adapter


ROOT = Path(__file__).resolve().parent


def report(label: str, passed: bool, detail: str) -> bool:
    """Print one PASS/FAIL verification line."""
    print(f"{'PASS' if passed else 'FAIL'}: {label} - {detail}")
    return passed


def main() -> int:
    """Run export-format and 250-person end-to-end checks."""
    results = []
    spec = spec_adapter.load_design_spec(ROOT / "specs" / "temp_spec.json")
    people, problems = load_people(ROOT / "sample_data" / "test_250.csv")
    person = people[0]

    try:
        ExportSettings(format="jpeg")
    except ValueError:
        invalid_rejected = True
    else:
        invalid_rejected = False
    results.append(report("Invalid settings rejected", invalid_rejected, "unsupported format raises ValueError"))

    png_cases = (
        (ExportSettings("png", 300), (709, 1087), "300 DPI with bleed"),
        (ExportSettings("png", 300, bleed=False), (638, 1016), "300 DPI trim"),
        (ExportSettings("png", 150), (354, 543), "150 DPI about half size"),
    )
    for settings, expected, label in png_cases:
        with Image.open(io.BytesIO(export_card(spec, person, settings))) as image:
            results.append(report(label, image.size == expected, f"{image.width} x {image.height} px"))

    svg = export_card(spec, person, ExportSettings("svg")).decode("utf-8")
    svg_vector = all(element in svg for element in ("<text", "<rect", "<circle"))
    results.append(report(
        "SVG remains vector",
        svg_vector,
        "text, rectangle, and circle primitives remain SVG elements",
    ))
    pdf = PdfReader(io.BytesIO(export_card(spec, person, ExportSettings("pdf"))))
    embedded = any(
        any(key in font.get_object().get("/FontDescriptor", {}).get_object()
            for key in ("/FontFile", "/FontFile2", "/FontFile3"))
        for font in pdf.pages[0]["/Resources"]["/Font"].get_object().values()
    )
    pdf_box = pdf.pages[0].mediabox
    expected_size = (60 / 25.4 * 72, 92 / 25.4 * 72)
    pdf_ok = (
        len(pdf.pages) == 1
        and abs(float(pdf_box.width) - expected_size[0]) < 0.5
        and abs(float(pdf_box.height) - expected_size[1]) < 0.5
        and embedded
    )
    results.append(report("Vector PDF page and embedded fonts", pdf_ok,
                          f"{len(pdf.pages)} page(s), {float(pdf_box.width):.2f} x "
                          f"{float(pdf_box.height):.2f} pt, fonts embedded={embedded}"))

    landscape = PdfReader(io.BytesIO(
        export_card(spec, person, ExportSettings("pdf", orientation="landscape"))
    )).pages[0].mediabox
    results.append(report("Landscape swaps dimensions", float(landscape.width) > float(landscape.height),
                          f"{float(landscape.width):.2f} x {float(landscape.height):.2f} pt"))

    expected_problem_rows = {21, 22, 23, 26}
    csv_ok = len(problems) == 4 and {problem["row"] for problem in problems} == expected_problem_rows
    results.append(report("CSV invalid rows include row numbers", csv_ok,
                          f"{len(problems)} bad rows: {[problem['row'] for problem in problems]}"))

    started = time.perf_counter()
    batch = export_batch(
        spec,
        people,
        ExportSettings("png", 150),
        skipped_rows=problems,
    )
    elapsed = time.perf_counter() - started
    with zipfile.ZipFile(io.BytesIO(batch)) as archive:
        names = archive.namelist()
        report_data = json.loads(archive.read("report.json"))
        output_count = len(names) - 1
        has_id_names = all(
            Path(name).stem.split("-", 1)[0].startswith("P")
            for name in names
            if name != "report.json"
        )
        batch_ok = (
            output_count == len(people)
            and report_data["totals"]["exported"] == len(people)
            and report_data["totals"]["skipped_rows"] == len(problems)
            and len(report_data["people"]) == len(people)
            and "report.json" in names
            and has_id_names
        )
    print(f"Batch of {len(people) + len(problems)} rows completed in {elapsed:.2f}s.")
    results.append(report("250-row batch completes and ZIP is complete", batch_ok,
                          f"{output_count} card files, {len(problems)} skipped rows, "
                          f"{report_data['totals']['failed']} export failures"))
    if all(results):
        print("Phase 5A verification complete.")
        return 0
    print("Phase 5A verification failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
