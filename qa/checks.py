"""Run independent quality checks against a rendered card."""

from __future__ import annotations

import math
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from PIL import Image

from render import spec_adapter
from render.renderer import ASSETS_DIR, _asset_ratio, _find_asset
from render.text_fit import find_font_file, measure_text_bounds


SVG_NS = "{http://www.w3.org/2000/svg}"
ALLOWED_OVERLAP_PAIRS = frozenset({
    frozenset(("event-name", "event-band")),
    frozenset(("person-photo", "photo-frame")),
})


@dataclass(frozen=True)
class Issue:
    """One actionable QA result for a card."""

    check: str
    severity: str
    person_id: str | None
    message: str


def run_qa(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
) -> list[Issue]:
    """Run every check independently and turn check failures into issues."""
    issues: list[Issue] = []
    try:
        card_person_id = spec_adapter.person_id(person)
    except Exception as error:
        card_person_id = None
        issues.append(Issue(
            "empty_fields", "error", None,
            f"Person ID could not be read: {error}",
        ))
    checks = (
        ("text_overflow", _check_text_overflow),
        ("logo_aspect_ratio", _check_logo_aspect_ratio),
        ("contrast", _check_contrast),
        ("overlap", _check_overlap),
        ("empty_fields", _check_empty_fields),
        ("data_match", _check_data_match),
        ("resolution", _check_resolution),
    )
    for name, check_function in checks:
        try:
            issues.extend(check_function(spec, person, svg, layout, theme, card_person_id))
        except Exception as error:
            issues.append(Issue(
                name,
                "error",
                card_person_id,
                f"The {name.replace('_', ' ')} check could not run: {error}",
            ))
    return issues


def _check_text_overflow(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
    person_id: str | None,
) -> list[Issue]:
    """Measure rendered text and check its box and the card's safe area."""
    del person
    root = ElementTree.fromstring(svg)
    elements = _layout_elements(layout)
    by_id = {str(item.get("id")): item for item in elements if item.get("id") is not None}
    by_id.update({
        f"logo-{item['data']}": item
        for item in elements
        if item.get("type") == "logo" and isinstance(item.get("data"), str)
    })
    parents = {child: parent for parent in root.iter() for child in parent}
    canvas_width, canvas_height, trim_x, trim_y, trim_width, trim_height = (
        spec_adapter.canvas_geometry(spec)
    )
    del canvas_width, canvas_height
    inset = spec_adapter.safe_inset(spec)
    safe = (trim_x + inset, trim_y + inset, trim_x + trim_width - inset, trim_y + trim_height - inset)
    fonts = theme.get("fonts")
    font_candidates = []
    if isinstance(fonts, dict):
        for key in ("heading", "body"):
            values = fonts.get(key, [])
            if isinstance(values, list):
                font_candidates.extend(value for value in values if isinstance(value, str))
    issues: list[Issue] = []
    for text in root.iter(f"{SVG_NS}text"):
        element_id = text.get("id", "unidentified text")
        source_element = by_id.get(element_id)
        if source_element is None:
            source_element = _ancestor_layout_element(text, parents, by_id)
        box = _text_box(text, source_element, layout, safe)
        family = text.get("font-family", "").replace('"', "").replace("'", "")
        families = [part.strip() for part in family.split(",") if part.strip()] or font_candidates
        weight = text.get("font-weight", "400")
        _, font_path = find_font_file(families, weight)
        font_size = float(text.get("font-size", "0"))
        if font_size <= 0:
            raise ValueError(f"Text element {element_id!r} has no positive font size")
        text_lines = list(text.findall(f"{SVG_NS}tspan"))
        if not text_lines:
            text_lines = [text]
        element_problems: list[str] = []
        for line in text_lines:
            value = "".join(line.itertext())
            x = float(line.get("x", text.get("x", "0")))
            baseline = float(line.get("y", text.get("y", "0")))
            anchor = text.get("text-anchor", "start")
            ink_left, ink_right, ascent, descent, advance = measure_text_bounds(
                value, font_path, font_size
            )
            origin = x - advance / 2 if anchor == "middle" else x - advance if anchor == "end" else x
            left, right = origin + ink_left, origin + ink_right
            if text.get("dominant-baseline") == "middle":
                offset = (ascent - descent) / 2
                top, bottom = baseline - offset - descent, baseline - offset + ascent
            else:
                top, bottom = baseline - ascent, baseline + descent
            if left < box[0] - 1e-6 or right > box[2] + 1e-6 or top < box[1] - 1e-6 or bottom > box[3] + 1e-6:
                element_problems.append("outside its text box")
            if left < safe[0] - 1e-6 or right > safe[2] + 1e-6 or top < safe[1] - 1e-6 or bottom > safe[3] + 1e-6:
                element_problems.append("outside the 3 mm safe area")
        if element_problems:
            issues.append(Issue(
                "text_overflow", "error", person_id,
                f"Text in {element_id} overflows {', and '.join(dict.fromkeys(element_problems))}.",
            ))
        if text.get("data-shortened") == "true":
            issues.append(Issue(
                "text_overflow", "warning", person_id,
                f"Text in {element_id} was shortened with an ellipsis to fit.",
            ))
    return issues


def _check_logo_aspect_ratio(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
    person_id: str | None,
) -> list[Issue]:
    """Compare each embedded logo's drawn ratio with its source asset."""
    del spec, person, layout, theme
    root = ElementTree.fromstring(svg)
    issues = []
    for logo in root.iter():
        logo_name = logo.get("id", "")
        if not logo_name.startswith("logo-") or logo.get("data-logo-status") is None:
            continue
        if logo.get("data-logo-status") == "placeholder":
            issues.append(Issue(
                "logo_aspect_ratio", "warning", person_id,
                f"Logo {logo_name.removeprefix('logo-')} is a placeholder; an aspect ratio cannot be verified (fallback was used).",
            ))
            continue
        path = _find_asset(logo_name.removeprefix("logo-"))
        if path is None:
            raise FileNotFoundError(f"Source asset for embedded {logo_name} was not found under {ASSETS_DIR}")
        width = float(logo.get("width", "0"))
        height = float(logo.get("height", "0"))
        if width <= 0 or height <= 0:
            issues.append(Issue(
                "logo_aspect_ratio", "error", person_id,
                f"Logo {logo_name} has no positive drawn width and height.",
            ))
            continue
        source_ratio = _asset_ratio(path)
        drawn_ratio = width / height
        if not math.isclose(drawn_ratio, source_ratio, rel_tol=0.01):
            issues.append(Issue(
                "logo_aspect_ratio", "error", person_id,
                f"Logo {logo_name} is drawn at a {drawn_ratio:.3f}:1 ratio; its source is {source_ratio:.3f}:1 (tolerance 1%).",
            ))
    return issues


def _check_contrast(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
    person_id: str | None,
) -> list[Issue]:
    """Check each text node against the theme-resolved background beneath it."""
    del spec
    root = ElementTree.fromstring(svg)
    elements = _layout_elements(layout)
    by_id = {str(item.get("id")): item for item in elements if item.get("id") is not None}
    by_id.update({
        f"logo-{item['data']}": item
        for item in elements
        if item.get("type") == "logo" and isinstance(item.get("data"), str)
    })
    parents = {child: parent for parent in root.iter() for child in parent}
    colors = theme.get("colors")
    role_colors = theme.get("role_colors")
    if not isinstance(colors, dict) or not isinstance(role_colors, dict):
        raise ValueError("Theme colors and role_colors must be objects")
    role = spec_adapter.person_value(person, "role")
    role_background = role_colors.get(role) if isinstance(role, str) else None
    canvas_background = _theme_color(colors, "background")
    issues = []
    for text in root.iter(f"{SVG_NS}text"):
        element_id = text.get("id", "")
        source_element = by_id.get(element_id)
        if source_element is None:
            source_element = _ancestor_layout_element(text, parents, by_id)
        foreground = _text_foreground(element_id, source_element, colors, text)
        point = _text_point(text)
        background = _background_at(
            point, elements, colors, role_background, canvas_background, source_element
        )
        ratio = _contrast_ratio(foreground, background)
        if ratio < 4.5:
            issues.append(Issue(
                "contrast", "error", person_id,
                f"Text in {element_id or 'unidentified text'} ({foreground} on {background}) has {ratio:.2f}:1 contrast; at least 4.5:1 is required.",
            ))
    return issues


def _check_overlap(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
    person_id: str | None,
) -> list[Issue]:
    """Report intersecting layout boxes except for documented background pairs."""
    del spec, person, svg, theme
    elements = _layout_elements(layout)
    boxes = [(item, _overlap_box(item)) for item in elements]
    issues = []
    for index, (first, first_box) in enumerate(boxes):
        for second, second_box in boxes[index + 1:]:
            first_id, second_id = str(first.get("id", "element")), str(second.get("id", "element"))
            if frozenset((first_id, second_id)) in ALLOWED_OVERLAP_PAIRS:
                continue
            if _boxes_overlap(first_box, second_box):
                issues.append(Issue(
                    "overlap", "error", person_id,
                    f"{first_id} overlaps {second_id}; their layout boxes intersect unintentionally.",
                ))
    return issues


def _check_empty_fields(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
    person_id: str | None,
) -> list[Issue]:
    """Report absent source fields and identify any visible fallback."""
    del theme
    root = ElementTree.fromstring(svg)
    issues: list[Issue] = []
    name = spec_adapter.person_value(person, "name")
    if name is None or not name.strip():
        fallback_used = "NAME NOT PROVIDED" in _text_content(root)
        issues.append(Issue(
            "empty_fields", "error", person_id,
            f"Name is empty; {'a visible fallback was used' if fallback_used else 'no fallback was used'}.",
        ))
    role = spec_adapter.person_value(person, "role")
    if role is None or not role.strip():
        issues.append(Issue(
            "empty_fields", "error", person_id,
            "Role is missing; no fallback was used.",
        ))
    identifier = spec_adapter.person_id(person)
    if identifier is None or not identifier.strip():
        issues.append(Issue(
            "empty_fields", "error", person_id,
            "ID is missing; the attendance QR fallback was to omit the code.",
        ))
    photo_path = spec_adapter.person_photo_path(person)
    photo = root.find(f".//*[@id='person-photo']")
    photo_is_fallback = photo is not None and photo.get("data-photo-status") == "fallback"
    if photo_path is None or not photo_path.is_file():
        issues.append(Issue(
            "empty_fields", "warning" if photo_is_fallback else "error", person_id,
            f"Photo is {'missing' if photo_path is None else 'not found'}; "
            f"{'an initials fallback was used' if photo_is_fallback else 'no fallback was used'}.",
        ))
    for logo_element in (item for item in _layout_elements(layout) if item.get("type") == "logo"):
        name_value = logo_element.get("data")
        if not isinstance(name_value, str) or not name_value:
            continue
        logo = root.find(f".//*[@id='logo-{name_value}']")
        if logo is None or logo.get("data-logo-status") != "embedded":
            fallback_used = logo is not None and logo.get("data-logo-status") == "placeholder"
            issues.append(Issue(
                "empty_fields", "warning" if fallback_used else "error", person_id,
                f"Logo {name_value} is missing; {'a placeholder fallback was used' if fallback_used else 'no fallback was used'}.",
            ))
    event_name = spec_adapter.event_value(spec, "name")
    if event_name is None or not event_name.strip():
        fallback_used = "EVENT NAME" in _text_content(root)
        issues.append(Issue(
            "empty_fields", "warning" if fallback_used else "error", person_id,
            f"Event name is null or empty; {'a visible fallback was used' if fallback_used else 'no fallback was used'}.",
        ))
    return issues


def _check_data_match(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
    person_id: str | None,
) -> list[Issue]:
    """Compare visible name and role and QR identity with normalized source data."""
    del spec, theme
    root = ElementTree.fromstring(svg)
    elements = _layout_elements(layout)
    text_by_id = {node.get("id"): node for node in root.iter(f"{SVG_NS}text")}
    issues: list[Issue] = []
    for element in elements:
        if element.get("type") != "text":
            continue
        field = element.get("data")
        if field not in {"person.name", "person.role", "person.id"}:
            continue
        field_name = str(field).removeprefix("person.")
        source = spec_adapter.person_value(person, field_name)
        rendered_node = text_by_id.get(str(element.get("id")))
        rendered = "".join(rendered_node.itertext()) if rendered_node is not None else None
        shortened = rendered_node is not None and rendered_node.get("data-shortened") == "true"
        if (
            source is None
            or rendered is None
            or not _same_card_text(rendered, source, shortened=shortened)
        ):
            issues.append(Issue(
                "data_match", "error", person_id,
                f"Card text for {field_name} does not match the source data.",
            ))
    role = spec_adapter.person_value(person, "role")
    role_label_node = text_by_id.get("role-label")
    role_label = "".join(role_label_node.itertext()) if role_label_node is not None else None
    if role and role_label is not None and not _same_card_text(role_label, role):
        issues.append(Issue(
            "data_match", "error", person_id,
            "Card role label does not match the source role.",
        ))
    identifier = spec_adapter.person_id(person)
    qr = root.find(".//*[@data-qr-payload]")
    if identifier and qr is not None:
        payload = qr.get("data-qr-payload", "")
        if not payload.endswith(identifier):
            issues.append(Issue(
                "data_match", "error", person_id,
                "Attendance QR does not contain the source ID.",
            ))
    return issues


def _check_resolution(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    svg: str,
    layout: dict[str, Any],
    theme: dict[str, Any],
    person_id: str | None,
) -> list[Issue]:
    """Export at the requested DPI and verify expected 60 by 92 mm pixels."""
    del person, layout, theme
    dpi = spec_adapter.requested_dpi(spec)
    canvas_width, canvas_height, _, _, _, _ = spec_adapter.canvas_geometry(spec)
    expected = (
        round(canvas_width * dpi / 25.4),
        round(canvas_height * dpi / 25.4),
    )
    import cairosvg

    with tempfile.TemporaryDirectory(prefix="card-qa-") as directory:
        png_path = Path(directory) / "card.png"
        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(png_path), dpi=dpi)
        with Image.open(png_path) as image:
            actual = image.size
    if actual != expected:
        return [Issue(
            "resolution", "error", person_id,
            f"PNG resolution is {actual[0]} x {actual[1]} px; expected {expected[0]} x {expected[1]} px at {dpi} DPI for a 60 x 92 mm card.",
        )]
    return []


def _layout_elements(layout: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the validated layout element list."""
    elements = layout.get("elements")
    if not isinstance(elements, list) or not all(isinstance(item, dict) for item in elements):
        raise ValueError("Layout elements must be an array of objects")
    return elements


def _layout_box(element: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return a layout element's left, top, right, and bottom."""
    position, size = element.get("position"), element.get("size")
    if not isinstance(position, dict) or not isinstance(size, dict):
        raise ValueError(f"Layout element {element.get('id', '(unnamed)')} has no position or size")
    x, y = float(position["x"]), float(position["y"])
    width, height = float(size["width"]), float(size["height"])
    return x, y, x + width, y + height


def _overlap_box(element: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return a layout box using the renderer's centered text positioning."""
    left, top, right, bottom = _layout_box(element)
    if element.get("type") != "text":
        return left, top, right, bottom
    width = min(right - left, float(element.get("max_width", right - left)))
    alignment = element.get("alignment", "start")
    if alignment == "middle":
        left -= width / 2
    elif alignment == "end":
        left -= width
    return left, top - (bottom - top) / 2, left + width, top + (bottom - top) / 2


def _text_box(
    text: ElementTree.Element,
    source_element: dict[str, Any] | None,
    layout: dict[str, Any],
    safe: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Find the configured text box for a regular or fallback SVG text node."""
    if source_element is not None:
        x, y, right, bottom = _layout_box(source_element)
        element_type = source_element.get("type")
        if element_type == "text":
            width = min(right - x, float(source_element.get("max_width", right - x)))
            anchor = text.get("text-anchor", source_element.get("alignment", "start"))
            left = x - width / 2 if anchor == "middle" else x - width if anchor == "end" else x
            return left, y - (bottom - y) / 2, left + width, y + (bottom - y) / 2
        return x, y, right, bottom
    role_area = layout.get("role_area")
    if text.get("id") == "role-label" and isinstance(role_area, dict):
        return safe
    x, y = float(text.get("x", "0")), float(text.get("y", "0"))
    size = float(text.get("font-size", "0"))
    return x - size / 2, y - size / 2, x + size / 2, y + size / 2


def _ancestor_layout_element(
    text: ElementTree.Element,
    parents: dict[ElementTree.Element, ElementTree.Element],
    by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Find a layout element enclosing a nested fallback text node."""
    ancestor = parents.get(text)
    while ancestor is not None:
        match = by_id.get(ancestor.get("id", ""))
        if match is not None:
            return match
        ancestor = parents.get(ancestor)
    return None


def _text_foreground(
    element_id: str,
    source_element: dict[str, Any] | None,
    colors: dict[str, Any],
    text: ElementTree.Element,
) -> str:
    """Resolve standard text colors by theme name, retaining renderer fallbacks."""
    theme_color = text.get("data-theme-color")
    if theme_color is not None:
        return _theme_color(colors, theme_color)
    if element_id == "role-label":
        return _theme_color(colors, "text_on_primary")
    if source_element is not None and source_element.get("type") == "text":
        return _theme_color(colors, str(source_element.get("color")))
    fill = text.get("fill")
    if fill == "#FFFFFF" and element_id == "person-photo":
        return _theme_color(colors, "text_on_primary")
    if isinstance(fill, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", fill):
        return fill
    return _theme_color(colors, "text")


def _text_point(text: ElementTree.Element) -> tuple[float, float]:
    """Return a text node's anchor point for background lookup."""
    return float(text.get("x", "0")), float(text.get("y", "0"))


def _background_at(
    point: tuple[float, float],
    elements: list[dict[str, Any]],
    colors: dict[str, Any],
    role_background: Any,
    default: str,
    source_element: dict[str, Any] | None,
) -> str:
    """Resolve the smallest layout rectangle containing the text anchor."""
    x, y = point
    if source_element is not None and source_element.get("type") in {"photo", "logo"}:
        return _theme_color(colors, str(source_element.get("color")))
    candidates = []
    for element in elements:
        if element.get("type") != "rect":
            continue
        left, top, right, bottom = _layout_box(element)
        if left <= x <= right and top <= y <= bottom:
            candidates.append(( (right - left) * (bottom - top), element))
    if not candidates:
        return default
    element = min(candidates, key=lambda item: item[0])[1]
    if element.get("role_area") is True:
        if not isinstance(role_background, str):
            raise ValueError("Theme has no role color for this person's role")
        return role_background
    return _theme_color(colors, str(element.get("color")))


def _theme_color(colors: dict[str, Any], name: str) -> str:
    """Resolve a valid six-digit theme color by its layout name."""
    value = colors.get(name)
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValueError(f"Theme color {name!r} is missing or invalid")
    return value


def _contrast_ratio(first: str, second: str) -> float:
    """Return the WCAG contrast ratio for two RGB colors."""
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _boxes_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    """Return whether two positive-area boxes intersect."""
    return first[0] < second[2] and second[0] < first[2] and first[1] < second[3] and second[1] < first[3]


def _text_content(root: ElementTree.Element) -> str:
    """Collect rendered text for checking visible fallback labels."""
    return "".join(root.itertext())


def _same_card_text(rendered: str, source: str, *, shortened: bool = False) -> bool:
    """Compare text across case and wrapping, allowing flagged ellipsis truncation."""
    normalize = lambda value: re.sub(r"\s+", "", value).casefold()
    visible, expected = normalize(rendered), normalize(source)
    if visible == expected:
        return True
    return shortened and visible.endswith("…") and expected.startswith(visible[:-1])
