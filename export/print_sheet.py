"""Compose vector card artwork into printable, crop-marked PDF sheets."""

from __future__ import annotations

import io
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any
from xml.etree import ElementTree

from export.exporters import _load_cairosvg
from export.settings import ExportSettings, PrintSheetSettings
from qa import run_qa
from qa.report import issues_to_dict
from render import spec_adapter
from render.loaders import load_layout, load_theme
from render.renderer import render_card


SVG_NS = "http://www.w3.org/2000/svg"
PAGE_SIZES_MM = {"A4": (210.0, 297.0), "A3": (297.0, 420.0)}
PAGE_MARGIN_MM = 10.0
MIN_CARD_GAP_MM = 8.0
CROP_MARK_LENGTH_MM = 4.0
CROP_MARK_WIDTH_MM = 0.25
CROP_MARK_CLEARANCE_MM = 0.25
CROP_MARK_GAP_CLEARANCE_MM = 0.5


def print_sheet_layout(
    paper: str,
    settings: PrintSheetSettings | ExportSettings | Mapping[str, Any],
) -> dict[str, float | int | str]:
    """Return the usable grid geometry and cards-per-page for a sheet."""
    if paper not in PAGE_SIZES_MM:
        raise ValueError("paper must be 'A4' or 'A3'")
    options = _settings_values(settings)
    page_width, page_height = PAGE_SIZES_MM[paper]
    if options["orientation"] == "landscape":
        page_width, page_height = page_height, page_width

    canvas_width, canvas_height, bleed = _card_geometry(options["bleed"])
    mark_extension = _mark_extension(bleed) if options["crop_marks"] else 0.0
    minimum_gap = _minimum_gap(bleed) if options["crop_marks"] else MIN_CARD_GAP_MM
    gap = max(MIN_CARD_GAP_MM, minimum_gap)
    available_width = page_width - 2 * PAGE_MARGIN_MM
    available_height = page_height - 2 * PAGE_MARGIN_MM
    columns = _count_fit(canvas_width, gap, mark_extension, available_width)
    rows = _count_fit(canvas_height, gap, mark_extension, available_height)
    return {
        "paper": paper,
        "orientation": options["orientation"],
        "bleed": options["bleed"],
        "crop_marks": options["crop_marks"],
        "page_width_mm": page_width,
        "page_height_mm": page_height,
        "card_width_mm": canvas_width,
        "card_height_mm": canvas_height,
        "margin_mm": PAGE_MARGIN_MM,
        "gap_mm": gap,
        "gap_increased": gap > MIN_CARD_GAP_MM,
        "columns": columns,
        "rows": rows,
        "cards_per_page": columns * rows,
    }


def export_print_sheet(
    spec: spec_adapter.DesignSpec,
    people: Sequence[spec_adapter.Person],
    paper: str,
    settings: PrintSheetSettings | ExportSettings | Mapping[str, Any],
    *,
    report: dict[str, Any] | None = None,
    skipped_rows: Sequence[dict[str, int | str]] = (),
) -> bytes:
    """Return a vector PDF sheet; optionally populate a batch-style report."""
    geometry = print_sheet_layout(paper, settings)
    options = _settings_values(settings)
    layout = load_layout(spec_adapter.spec_layout(spec))
    theme = load_theme(spec_adapter.spec_theme(spec))
    ordered_people = list(people)
    if options["group_by_role"]:
        role_order = {role: index for index, role in enumerate(spec_adapter.ROLES)}

        def role_position(person: spec_adapter.Person) -> int:
            try:
                return role_order[spec_adapter.person_role(person)]
            except (TypeError, ValueError):
                return len(role_order)

        ordered_people.sort(key=role_position)

    records: list[dict[str, Any]] = []
    valid_cards: list[tuple[spec_adapter.Person, str]] = []
    qa_issue_count = 0
    for person in ordered_people:
        person_id = _person_id(person)
        issue_dicts: list[dict[str, str | None]] = []
        try:
            svg = render_card(spec, person)
            issues = run_qa(spec, person, svg, layout, theme)
            issue_dicts = issues_to_dict(issues)
            qa_issue_count += len(issue_dicts)
            errors = [issue for issue in issues if issue.severity == "error"]
            if errors:
                records.append({
                    "id": person_id,
                    "status": "failed",
                    "reason": "QA reported error(s); card skipped",
                    "qa_issues": issue_dicts,
                })
                continue
            valid_cards.append((person, svg))
            records.append({
                "id": person_id,
                "role": spec_adapter.person_role(person),
                "status": "exported",
                "qa_issues": issue_dicts,
            })
        except Exception as error:
            records.append({
                "id": person_id,
                "status": "failed",
                "reason": str(error),
                "qa_issues": issue_dicts,
            })

    per_page = int(geometry["cards_per_page"])
    page_count = max(1, math.ceil(len(valid_cards) / per_page))
    pdf_bytes = _compose_pdf(spec, valid_cards, geometry, options, page_count)
    if report is not None:
        report.update({
            "totals": {
                "people": len(ordered_people),
                "exported": len(valid_cards),
                "failed": len(ordered_people) - len(valid_cards),
                "skipped_rows": len(skipped_rows),
                "qa_issues": qa_issue_count,
                "pages": page_count,
            },
            "people": records,
            "skipped_rows": list(skipped_rows),
            "settings": {
                **options,
                "paper": paper,
                "cards_per_page": per_page,
                "columns": geometry["columns"],
                "rows": geometry["rows"],
                "gap_mm": geometry["gap_mm"],
                "gap_increased": geometry["gap_increased"],
            },
        })
    return pdf_bytes


def _compose_pdf(
    spec: spec_adapter.DesignSpec,
    cards: Sequence[tuple[spec_adapter.Person, str]],
    geometry: Mapping[str, float | int | str],
    options: Mapping[str, Any],
    page_count: int,
) -> bytes:
    """Compose all card SVGs and crop marks into full-page SVGs for CairoSVG."""
    width = float(geometry["page_width_mm"])
    height = float(geometry["page_height_mm"])
    card_width = float(geometry["card_width_mm"])
    card_height = float(geometry["card_height_mm"])
    columns = int(geometry["columns"])
    rows = int(geometry["rows"])
    gap = float(geometry["gap_mm"])
    bleed = 3.0 if options["bleed"] else 0.0
    mark_extension = _mark_extension(bleed) if options["crop_marks"] else 0.0
    grid_width = columns * card_width + max(0, columns - 1) * gap
    grid_height = rows * card_height + max(0, rows - 1) * gap
    first_x = (width - grid_width - 2 * mark_extension) / 2 + mark_extension
    first_y = (height - grid_height - 2 * mark_extension) / 2 + mark_extension
    page_svgs: list[str] = []
    event_name = spec_adapter.event_value(spec, "name")
    for page_index in range(page_count):
        root = ElementTree.Element(
            f"{{{SVG_NS}}}svg",
            {
                "width": f"{width:g}mm",
                "height": f"{height:g}mm",
                "viewBox": f"0 0 {width:g} {height:g}",
            },
        )
        ElementTree.SubElement(
            root,
            f"{{{SVG_NS}}}rect",
            {"x": "0", "y": "0", "width": f"{width:g}", "height": f"{height:g}", "fill": "#ffffff"},
        )
        defs = ElementTree.SubElement(root, f"{{{SVG_NS}}}defs")
        clip_id = f"sheet-trim-{page_index}"
        clip = ElementTree.SubElement(defs, f"{{{SVG_NS}}}clipPath", {"id": clip_id})
        ElementTree.SubElement(
            clip,
            f"{{{SVG_NS}}}rect",
            {"x": "0", "y": "0", "width": f"{card_width:g}", "height": f"{card_height:g}"},
        )
        start = page_index * int(geometry["cards_per_page"])
        page_cards = cards[start:start + int(geometry["cards_per_page"])]
        for position, (_, card_svg) in enumerate(page_cards):
            row, column = divmod(position, columns)
            x = first_x + column * (card_width + gap)
            y = first_y + row * (card_height + gap)
            _append_card(root, card_svg, x, y, clip_id, position)
            if options["crop_marks"]:
                _append_crop_marks(root, x, y, card_width, card_height, bleed)
        if options["page_labels"]:
            _append_page_label(root, width, height, page_index + 1, event_name)
        page_svgs.append(ElementTree.tostring(root, encoding="unicode"))

    cairosvg = _load_cairosvg()
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    for svg in page_svgs:
        writer.append(PdfReader(io.BytesIO(cairosvg.svg2pdf(bytestring=svg.encode("utf-8")))))
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _append_card(
    page_root: ElementTree.Element,
    svg: str,
    x: float,
    y: float,
    clip_id: str,
    card_index: int,
) -> None:
    """Place a card's SVG children without rasterizing or colliding its IDs."""
    source = ElementTree.fromstring(svg)
    _prefix_ids(source, f"card-{card_index}-")
    group = ElementTree.SubElement(
        page_root,
        f"{{{SVG_NS}}}g",
        {
            "transform": f"translate({x:g} {y:g})",
            "clip-path": f"url(#{clip_id})",
        },
    )
    artwork = ElementTree.SubElement(
        group,
        f"{{{SVG_NS}}}g",
        {"transform": "translate(-3 -3)"},
    )
    artwork.extend(list(source))


def _append_crop_marks(
    root: ElementTree.Element,
    x: float,
    y: float,
    card_width: float,
    card_height: float,
    bleed: float,
) -> None:
    """Draw four pairs of black crop-mark strokes outside the bleed box."""
    inset = max(bleed, 3.0) + CROP_MARK_CLEARANCE_MM + CROP_MARK_WIDTH_MM / 2
    trim_left, trim_top = x + bleed, y + bleed
    trim_right, trim_bottom = trim_left + card_width - 2 * bleed, trim_top + card_height - 2 * bleed
    stroke = f"{CROP_MARK_WIDTH_MM:g}"
    marks = (
        (trim_left - inset - CROP_MARK_LENGTH_MM, trim_top, trim_left - inset, trim_top),
        (trim_left, trim_top - inset - CROP_MARK_LENGTH_MM, trim_left, trim_top - inset),
        (trim_right + inset, trim_top, trim_right + inset + CROP_MARK_LENGTH_MM, trim_top),
        (trim_right, trim_top - inset - CROP_MARK_LENGTH_MM, trim_right, trim_top - inset),
        (trim_left - inset - CROP_MARK_LENGTH_MM, trim_bottom, trim_left - inset, trim_bottom),
        (trim_left, trim_bottom + inset, trim_left, trim_bottom + inset + CROP_MARK_LENGTH_MM),
        (trim_right + inset, trim_bottom, trim_right + inset + CROP_MARK_LENGTH_MM, trim_bottom),
        (trim_right, trim_bottom + inset, trim_right, trim_bottom + inset + CROP_MARK_LENGTH_MM),
    )
    for x1, y1, x2, y2 in marks:
        ElementTree.SubElement(
            root,
            f"{{{SVG_NS}}}line",
            {
                "x1": f"{x1:g}",
                "y1": f"{y1:g}",
                "x2": f"{x2:g}",
                "y2": f"{y2:g}",
                "stroke": "#000000",
                "stroke-width": stroke,
                "stroke-linecap": "butt",
                "data-crop-mark": "true",
            },
        )


def _append_page_label(
    root: ElementTree.Element,
    width: float,
    height: float,
    page_number: int,
    event_name: str | None,
) -> None:
    """Add a small grey page number and the event name when one exists."""
    from render.text_fit import find_font_file, measure_text

    font_family, font_path = find_font_file(["Arial", "Segoe UI"])
    style = {
        "font-family": font_family,
        "font-size": "2mm",
        "fill": "#777777",
    }
    number = ElementTree.SubElement(
        root,
        f"{{{SVG_NS}}}text",
        {"x": f"{PAGE_MARGIN_MM:g}", "y": f"{height - 4:g}", **style},
    )
    number.text = str(page_number)
    if event_name:
        maximum_width = width - 30
        measured_width = measure_text(event_name, font_path, 2.0)
        font_size = (
            min(2.0, 2.0 * maximum_width / measured_width)
            if measured_width > 0 else 2.0
        )
        label = ElementTree.SubElement(
            root,
            f"{{{SVG_NS}}}text",
            {
                "x": f"{width - PAGE_MARGIN_MM:g}",
                "y": f"{height - 4:g}",
                "text-anchor": "end",
                **style,
                "font-size": f"{font_size:g}mm",
            },
        )
        label.text = event_name


def _prefix_ids(root: ElementTree.Element, prefix: str) -> None:
    """Make every artwork ID unique and update SVG fragment references."""
    ids = {
        node.get("id"): f"{prefix}{node.get('id')}"
        for node in root.iter()
        if node.get("id") is not None
    }
    for node in root.iter():
        identifier = node.get("id")
        if identifier in ids:
            node.set("id", ids[identifier])
        for attribute, value in list(node.attrib.items()):
            value = re.sub(
                r"url\(#([^)]+)\)",
                lambda match: f"url(#{ids.get(match.group(1), match.group(1))})",
                value,
            )
            if attribute in {"href", f"{{http://www.w3.org/1999/xlink}}href"} and value.startswith("#"):
                value = f"#{ids.get(value[1:], value[1:])}"
            node.set(attribute, value)


def _count_fit(size: float, gap: float, mark_extension: float, available: float) -> int:
    """Find the maximum non-overlapping count inside the page margin."""
    count = 0
    while (count + 1) * size + count * gap + 2 * mark_extension <= available + 1e-9:
        count += 1
    if count < 1:
        raise ValueError("The card and crop marks do not fit within the paper margins")
    return count


def _card_geometry(has_bleed: bool) -> tuple[float, float, float]:
    return (60.0, 92.0, 3.0) if has_bleed else (54.0, 86.0, 0.0)


def _mark_extension(bleed: float) -> float:
    outside_trim = CROP_MARK_CLEARANCE_MM + CROP_MARK_WIDTH_MM / 2 + CROP_MARK_LENGTH_MM
    return outside_trim if bleed else 3.0 + outside_trim


def _minimum_gap(bleed: float) -> float:
    """Keep opposing marks clear of each other and both bleed boxes."""
    return max(
        MIN_CARD_GAP_MM,
        2 * _mark_extension(bleed) + CROP_MARK_GAP_CLEARANCE_MM,
    )


def _settings_values(
    settings: PrintSheetSettings | ExportSettings | Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize print-sheet options and retain compatible ExportSettings use."""
    if isinstance(settings, Mapping):
        values = dict(settings)
    else:
        values = {
            "orientation": getattr(settings, "orientation", "portrait"),
            "bleed": getattr(settings, "bleed", True),
            "crop_marks": getattr(settings, "crop_marks", True),
            "page_labels": getattr(settings, "page_labels", True),
            "group_by_role": getattr(settings, "group_by_role", False),
        }
    options = {
        "orientation": values.get("orientation", "portrait"),
        "bleed": values.get("bleed", True),
        "crop_marks": values.get("crop_marks", True),
        "page_labels": values.get("page_labels", True),
        "group_by_role": values.get("group_by_role", False),
    }
    PrintSheetSettings(**options)
    return options


def _person_id(person: spec_adapter.Person) -> str | None:
    """Read an ID for reports without preventing failure reporting."""
    try:
        return spec_adapter.person_id(person)
    except (TypeError, ValueError):
        return None
