"""Run focused checks for Phase 3 text fitting, photos, QR codes, and exports."""

from __future__ import annotations

import math
import sys
import tempfile
import warnings
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image
from pypdf import PdfReader

from render import spec_adapter
from render.renderer import render_card
from render.text_fit import find_font_file, measure_text


ROOT = Path(__file__).resolve().parent
SVG_NS = "{http://www.w3.org/2000/svg}"


def report(label: str, passed: bool, detail: str) -> bool:
    """Print one PASS/FAIL result."""
    print(f"{'PASS' if passed else 'FAIL'}: {label} - {detail}")
    return passed


def main() -> int:
    """Run all requested Phase 3 checks."""
    spec = spec_adapter.load_design_spec()
    people = spec_adapter.load_people()
    results: list[bool] = []
    svgs = [render_card(spec, person) for person in people]

    long_person = people[0]
    long_svg = svgs[0]
    layout = __import__("render.loaders", fromlist=["load_layout"]).load_layout("classic")
    name_element = next(item for item in layout["elements"] if item.get("id") == "person-name")
    long_text = spec_adapter.person_value(long_person, "name") or ""
    long_node = _by_id(long_svg, "person-name")
    font_family, font_path = find_font_file(["Arial", "Segoe UI"], str(name_element.get("weight", "400")))
    font_size = float(long_node.get("font-size", "0"))
    fitted_lines = [node.text or "" for node in long_node.findall(f"{SVG_NS}tspan")]
    measured_widths = [measure_text(line, font_path, font_size) for line in fitted_lines]
    max_width = float(name_element["max_width"])
    fits = (
        bool(fitted_lines)
        and all(width <= max_width + 1e-6 for width in measured_widths)
        and font_family in long_node.get("font-family", "")
        and "person-name-clip" in long_svg
    )
    results.append(report(
        "Long name stays inside its box using real font metrics",
        fits,
        f"font={font_family}, widths={', '.join(f'{value:.2f}mm' for value in measured_widths)}, limit={max_width:g}mm",
    ))
    shortened = long_node.get("data-shortened") == "true" and "".join(fitted_lines) != long_text
    results.append(report(
        "Shortened name sets the output flag",
        shortened,
        f"data-shortened={long_node.get('data-shortened')!r}",
    ))

    one_word_svg = svgs[1]
    accented_svg = svgs[2]
    names_rendered = "Cher" in _text_content(one_word_svg) and "Élodie Núñez" in _text_content(accented_svg)
    results.append(report("One-word and accented names render", names_rendered, "Cher and Élodie Núñez appear in SVG text"))

    missing_person = next(person for person in people if spec_adapter.person_photo_path(person) is None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        missing_svg = render_card(spec, missing_person)
    missing_markup = _by_id(missing_svg, "person-photo")
    expected_initials = __import__("render.photo", fromlist=["initials"]).initials(
        spec_adapter.person_value(missing_person, "name")
    )
    fallback_text = "".join(missing_markup.itertext())
    fallback_ok = (
        missing_markup.get("data-photo-status") == "fallback"
        and expected_initials in fallback_text
        and any("Person photo is missing" in str(item.message) for item in caught)
    )
    results.append(report("Missing photo shows initials with a warning", fallback_ok, f"fallback initials: {expected_initials}"))

    crop_results = []
    for person in people[:3]:
        photo_svg = svgs[people.index(person)]
        photo_node = _by_id(photo_svg, "person-photo")
        source_width, source_height = map(int, photo_node.get("data-source-size", "0 0").split())
        rendered_ratio = float(photo_node.get("width", "0")) / float(photo_node.get("height", "1"))
        crop_results.append(
            photo_node.get("data-photo-status") == "embedded"
            and math.isclose(rendered_ratio, source_width / source_height, rel_tol=1e-6)
            and f'id="person-photo-clip"' in photo_svg
        )
    results.append(report(
        "Tall, wide, and tiny photos crop without distortion",
        all(crop_results),
        "all three embedded image aspect ratios are preserved and clipped",
    ))

    qr_spec = spec_adapter.DesignSpec({**spec._data, "attendance_url_base": "https://example.invalid/attendance/"})
    qr_svg = render_card(qr_spec, people[0])
    qr_node = _by_id(qr_svg, "attendance-qr")
    qr_ok = (
        qr_node is not None
        and float(qr_node.get("data-qr-width-mm", "0")) >= 12
        and qr_node.get("data-qr-payload") == "https://example.invalid/attendance/" + (spec_adapter.person_id(people[0]) or "")
        and len(qr_node.findall(f"{SVG_NS}path")) >= 2
    )
    results.append(report("QR is vector and at least 12 mm wide", qr_ok, f"width={qr_node.get('data-qr-width-mm') if qr_node is not None else 'missing'} mm"))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        null_qr_svg = render_card(spec, people[0])
    qr_skipped = (
        _find_id(null_qr_svg, "attendance-qr") is None
        and any("attendance_url_base is null" in str(item.message) for item in caught)
    )
    results.append(report("Null attendance URL skips QR with a warning", qr_skipped, "no QR element was rendered"))

    geometry_ok = all(
        (root := ElementTree.fromstring(svg)).get("width") == "60mm"
        and root.get("height") == "92mm"
        and root.get("viewBox") == "0 0 60 92"
        for svg in svgs
    )
    results.append(report("Every sample SVG is 60 mm by 92 mm", geometry_ok, f"checked {len(svgs)} SVGs"))

    export_ok, export_detail = _check_exports(qr_svg)
    results.append(report("PDF and PNG export still work", export_ok, export_detail))

    if all(results):
        print("Phase 3 verification complete.")
        return 0
    print("Phase 3 verification failed. Fix failed items and run again.", file=sys.stderr)
    return 1


def _by_id(svg: str, element_id: str) -> ElementTree.Element:
    """Find an SVG element by ID or fail with an explicit verification error."""
    element = _find_id(svg, element_id)
    if element is None:
        raise ValueError(f"Expected SVG element id={element_id!r}")
    return element


def _find_id(svg: str, element_id: str) -> ElementTree.Element | None:
    """Find an SVG element by ID."""
    root = ElementTree.fromstring(svg)
    return root.find(f".//*[@id='{element_id}']")


def _text_content(svg: str) -> str:
    """Collect visible text in document order."""
    root = ElementTree.fromstring(svg)
    return "".join(node.text or "" for node in root.iter(f"{SVG_NS}tspan"))


def _check_exports(svg: str) -> tuple[bool, str]:
    """Export one rendered card and verify a readable PDF and PNG."""
    try:
        import cairosvg

        with tempfile.TemporaryDirectory(prefix="phase3-export-") as directory:
            pdf_path = Path(directory) / "card.pdf"
            png_path = Path(directory) / "card.png"
            cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=str(pdf_path))
            cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                write_to=str(png_path),
                output_width=709,
                output_height=1087,
            )
            pdf_pages = len(PdfReader(str(pdf_path)).pages)
            with Image.open(png_path) as image:
                png_size = image.size
            valid = pdf_pages == 1 and png_size == (709, 1087)
            return valid, f"PDF pages={pdf_pages}; PNG={png_size[0]}x{png_size[1]}"
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        return False, str(error)


if __name__ == "__main__":
    raise SystemExit(main())
