"""Validate layout JSON files against the project schema and print constraints."""

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import (
    ALLOWED_COLOR_NAMES,
    ALLOWED_ELEMENT_TYPES,
    CANVAS_HEIGHT_MM,
    CANVAS_WIDTH_MM,
    ELEMENT_PROPERTY_SPECS,
    LAYOUTS_DIR,
    MIN_QR_SIZE_MM,
    REQUIRED_LOGOS,
    SAFE_AREA_X_MAX,
    SAFE_AREA_X_MIN,
    SAFE_AREA_Y_MAX,
    SAFE_AREA_Y_MIN,
    is_within_safe_area,
)

HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?(?![0-9A-Fa-f])")
IMPORTANT_TYPES = {"text", "photo", "logo", "qr", "role_badge"}
COLOR_PROPERTIES = {"fill", "stroke", "color", "background", "border_color", "tint"}
ELEMENT_EXTRA_PROPERTIES = {
    "text": {
        "color",
        "optional",
        "collapse_if_empty",
        "collapse_group",
        "collapse_height",
    }
}


def _number(element: dict[str, Any], key: str) -> float | None:
    """Return a finite numeric property, rejecting booleans and missing values."""
    value = element.get(key)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        return None
    return float(value)


def _string_values(value: Any):
    """Yield every string value, including values nested in arrays or objects."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _string_values(child)


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open(encoding="utf-8") as json_file:
            data = json.load(json_file)
    except (OSError, json.JSONDecodeError) as error:
        return None, str(error)
    if not isinstance(data, dict):
        return None, "top-level JSON value must be an object"
    return data, None


def _validate_element(
    filename: str,
    element: Any,
    index: int,
    errors: list[str],
) -> None:
    if not isinstance(element, dict):
        errors.append(f"FAIL {filename} / element #{index}: expected an object")
        return

    element_type = element.get("type")
    label = element.get("field", element.get("src", element_type or f"#{index}"))
    if not isinstance(element_type, str) or element_type not in ALLOWED_ELEMENT_TYPES:
        errors.append(
            f"FAIL {filename} / element '{label}': unknown type {element_type!r}"
        )
        return

    spec = ELEMENT_PROPERTY_SPECS[element_type]
    allowed = (
        set(spec["required"])
        | set(spec["optional"])
        | ELEMENT_EXTRA_PROPERTIES.get(element_type, set())
    )
    for property_name in sorted(set(element) - allowed):
        errors.append(
            f"FAIL {filename} / element '{label}': unknown property "
            f"'{property_name}' for type '{element_type}'"
        )
    for property_name in sorted(set(spec["required"]) - set(element)):
        errors.append(
            f"FAIL {filename} / element '{label}': missing required property "
            f"'{property_name}'"
        )

    for property_name in COLOR_PROPERTIES.intersection(element):
        color_name = element[property_name]
        if not isinstance(color_name, str) or color_name not in ALLOWED_COLOR_NAMES:
            errors.append(
                f"FAIL {filename} / element '{label}': color '{color_name}' "
                f"in '{property_name}' is not an allowed color name"
            )

    if element_type == "text":
        minimum = _number(element, "min_font")
        maximum = _number(element, "max_font")
        if minimum is None:
            errors.append(
                f"FAIL {filename} / element '{label}': min_font must be numeric"
            )
        if maximum is None:
            errors.append(
                f"FAIL {filename} / element '{label}': max_font must be numeric"
            )
        if minimum is not None and maximum is not None and minimum > maximum:
            errors.append(
                f"FAIL {filename} / element '{label}': min_font {minimum:g} pt "
                f"exceeds max_font {maximum:g} pt"
            )

    if element_type == "logo":
        if element.get("fit") != "contain":
            errors.append(
                f"FAIL {filename} / element '{label}': logo fit must be 'contain'"
            )

    if element_type == "qr":
        width = _number(element, "w")
        height = _number(element, "h")
        if width is not None and width < MIN_QR_SIZE_MM:
            errors.append(
                f"FAIL {filename} / element '{label}': width {width:g} mm is below "
                f"the {MIN_QR_SIZE_MM:g} mm minimum"
            )
        if height is not None and height < MIN_QR_SIZE_MM:
            errors.append(
                f"FAIL {filename} / element '{label}': height {height:g} mm is below "
                f"the {MIN_QR_SIZE_MM:g} mm minimum"
            )

    if element_type in IMPORTANT_TYPES:
        x = _number(element, "x")
        y = _number(element, "y")
        width = _number(element, "w")
        height = _number(element, "h")
        if x is None or y is None:
            errors.append(
                f"FAIL {filename} / element '{label}': x and y must be numeric"
            )
        elif width is not None and height is not None:
            if not is_within_safe_area(x, y, width, height):
                errors.append(
                    f"FAIL {filename} / element '{label}': bounds "
                    f"x={x:g}, y={y:g}, w={width:g}, h={height:g} exceed "
                    f"safe area x={SAFE_AREA_X_MIN:g}..{SAFE_AREA_X_MAX:g}, "
                    f"y={SAFE_AREA_Y_MIN:g}..{SAFE_AREA_Y_MAX:g}"
                )
        elif width is not None:
            if (
                x < SAFE_AREA_X_MIN
                or x + width > SAFE_AREA_X_MAX
                or y < SAFE_AREA_Y_MIN
                or y > SAFE_AREA_Y_MAX
            ):
                errors.append(
                    f"FAIL {filename} / element '{label}': bounds "
                    f"x={x:g}..{x + width:g}, y={y:g} exceed safe area "
                    f"x={SAFE_AREA_X_MIN:g}..{SAFE_AREA_X_MAX:g}, "
                    f"y={SAFE_AREA_Y_MIN:g}..{SAFE_AREA_Y_MAX:g}"
                )
        elif not (
            SAFE_AREA_X_MIN <= x <= SAFE_AREA_X_MAX
            and SAFE_AREA_Y_MIN <= y <= SAFE_AREA_Y_MAX
        ):
            errors.append(
                f"FAIL {filename} / element '{label}': anchor "
                f"x={x:g}, y={y:g} exceeds safe area"
            )


def _warn_about_overlaps(filename: str, elements: list[Any]) -> None:
    """Warn about definite box overlaps and text boxes with unknown height."""
    boxes = []
    unknown_geometry = False
    for index, element in enumerate(elements):
        if not isinstance(element, dict) or element.get("type") not in IMPORTANT_TYPES:
            continue
        x = _number(element, "x")
        y = _number(element, "y")
        width = _number(element, "w")
        height = _number(element, "h")
        if None in (x, y, width, height):
            unknown_geometry = True
        if None not in (x, y, width, height):
            boxes.append(
                (
                    index,
                    str(element.get("field", element.get("src", element["type"]))),
                    x,
                    y,
                    width,
                    height,
                )
            )

    for left_index, left_name, lx, ly, lw, lh in boxes:
        for right_index, right_name, rx, ry, rw, rh in boxes:
            if right_index <= left_index:
                continue
            overlaps = lx < rx + rw and rx < lx + lw and ly < ry + rh and ry < ly + lh
            if overlaps:
                print(
                    f"WARN {filename} / elements '{left_name}' and "
                    f"'{right_name}': bounding boxes overlap"
                )
    if unknown_geometry:
        print(
            f"WARN {filename}: overlap check is partial because one or more "
            "important elements do not have complete bounding boxes"
        )


def validate_layout(path: Path) -> bool:
    """Validate one layout and print readable pass/fail messages."""
    filename = path.name
    layout, json_error = _load_json(path)
    if json_error is not None:
        print(f"FAIL {filename}: invalid JSON: {json_error}")
        return False

    errors: list[str] = []
    for key in ("id", "name", "canvas", "elements"):
        if key not in layout:
            errors.append(f"FAIL {filename}: missing required top-level key '{key}'")

    canvas = layout.get("canvas")
    if not isinstance(canvas, dict):
        errors.append(f"FAIL {filename}: canvas must be an object")
    else:
        canvas_width = canvas.get("width", canvas.get("canvas_width"))
        canvas_height = canvas.get("height", canvas.get("canvas_height"))
        if canvas_width != CANVAS_WIDTH_MM:
            errors.append(
                f"FAIL {filename} / canvas: width must be {CANVAS_WIDTH_MM:g} mm"
            )
        if canvas_height != CANVAS_HEIGHT_MM:
            errors.append(
                f"FAIL {filename} / canvas: height must be {CANVAS_HEIGHT_MM:g} mm"
            )

    all_values = list(_string_values(layout))
    for value in all_values:
        match = HEX_COLOR.search(value)
        if match:
            errors.append(
                f"FAIL {filename}: hex color '{match.group()}' is not allowed in layouts"
            )

    elements = layout.get("elements")
    if not isinstance(elements, list):
        errors.append(f"FAIL {filename}: elements must be a list")
        elements = []
    else:
        found_logos = set()
        for index, element in enumerate(elements):
            _validate_element(filename, element, index, errors)
            if isinstance(element, dict) and element.get("type") == "logo":
                found_logos.add(element.get("src"))
        for required_logo in REQUIRED_LOGOS:
            if required_logo not in found_logos:
                errors.append(
                    f"FAIL {filename}: missing required logo '{required_logo}'"
                )
        _warn_about_overlaps(filename, elements)

    if errors:
        for error in errors:
            print(error)
        return False

    print(f"PASS {filename}: JSON, schema, colors, and required logos are valid")
    print(f"PASS {filename}: all important elements inside safe area")
    print(f"PASS {filename}: text sizes and QR dimensions meet requirements")
    return True


def main() -> int:
    layout_paths = sorted(LAYOUTS_DIR.glob("*.json"))
    if not layout_paths:
        print(f"FAIL layouts: no JSON files found in {LAYOUTS_DIR}")
        return 1

    passed = True
    for layout_path in layout_paths:
        if not validate_layout(layout_path):
            passed = False
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
