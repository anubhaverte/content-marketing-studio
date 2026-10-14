"""Layout preparation helpers shared by card renderers."""

from collections.abc import Mapping
from typing import Any


def prepare_layout(
    layout: Mapping[str, Any],
    attendee: Mapping[str, Any],
) -> dict[str, Any]:
    """Remove blank collapsible elements and compact their associated rows."""
    elements = layout.get("elements")
    if not isinstance(elements, list):
        raise ValueError("Layout 'elements' must be a list")
    if any(not isinstance(element, Mapping) for element in elements):
        raise ValueError("Every layout element must be a mapping")

    prepared = dict(layout)
    prepared_elements = [dict(element) for element in elements]
    prepared["elements"] = prepared_elements

    omitted_rows: dict[str, list[tuple[float, float]]] = {}
    for element in prepared_elements:
        if not element.get("collapse_if_empty"):
            continue

        field = element.get("field")
        group = element.get("collapse_group")
        collapse_height = element.get("collapse_height")
        y = element.get("y")
        if not isinstance(field, str) or not field:
            raise ValueError("Collapsible elements must specify a field")
        if not isinstance(group, str) or not group:
            raise ValueError("Collapsible elements must specify a collapse_group")
        if (
            isinstance(collapse_height, bool)
            or not isinstance(collapse_height, (int, float))
            or collapse_height <= 0
        ):
            raise ValueError("Collapsible elements must specify a positive collapse_height")
        if isinstance(y, bool) or not isinstance(y, (int, float)):
            raise ValueError("Collapsible elements must specify a numeric y coordinate")

        value = attendee.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            omitted_rows.setdefault(group, []).append((float(y), float(collapse_height)))

    visible_elements = []
    for element in prepared_elements:
        group = element.get("collapse_group")
        y = element.get("y")
        if element.get("collapse_if_empty"):
            field = element["field"]
            value = attendee.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

        if isinstance(group, str) and isinstance(y, (int, float)) and not isinstance(y, bool):
            shift = sum(
                height
                for row_y, height in omitted_rows.get(group, [])
                if y > row_y
            )
            if shift:
                element["y"] = y - shift
        visible_elements.append(element)

    prepared["elements"] = visible_elements
    return prepared
