"""Read and normalize the temporary Design Spec format."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMP_SPEC_PATH = PROJECT_ROOT / "specs" / "temp_spec.json"
PEOPLE_PATH = PROJECT_ROOT / "sample_data" / "people.json"
ROLES = ("participant", "organizer", "mentor", "volunteer")


@dataclass(frozen=True)
class DesignSpec:
    """Normalized Design Spec values used by the renderer."""

    _data: dict[str, Any]


@dataclass(frozen=True)
class Person:
    """Normalized person values used by the renderer."""

    _data: dict[str, Any]
    _source_file: str | None = None


def normalize_design_spec(spec: DesignSpec | Mapping[str, Any]) -> DesignSpec:
    """Return a DesignSpec from the normalized model or a decoded JSON object."""
    if isinstance(spec, DesignSpec):
        return spec
    if not isinstance(spec, Mapping):
        raise ValueError("Design Spec input must be a DesignSpec or JSON object")
    return DesignSpec(dict(spec))


def normalize_person(
    person: Person | Mapping[str, Any],
    *,
    source_file: str | Path | None = None,
) -> Person:
    """Return a Person from the normalized model or a decoded people object."""
    if isinstance(person, Person):
        return person
    if not isinstance(person, Mapping):
        raise ValueError("Person input must be a Person or JSON object")
    return Person(dict(person), str(source_file) if source_file is not None else None)


def load_design_spec(path: Path = TEMP_SPEC_PATH) -> DesignSpec:
    """Load the temporary JSON spec and retain its file path in parse errors."""
    try:
        with path.open(encoding="utf-8") as spec_file:
            data = json.load(spec_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read Design Spec {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"Design Spec must be a JSON object: {path}")
    return DesignSpec(data)


def load_people(path: Path = PEOPLE_PATH) -> list[Person]:
    """Load people data and return normalized person records."""
    try:
        with path.open(encoding="utf-8") as people_file:
            data = json.load(people_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read people data {path}: {error}") from error
    if not isinstance(data, list):
        raise ValueError(f"People data must be a JSON array: {path}")
    if not all(isinstance(person, dict) for person in data):
        raise ValueError(f"Every people entry must be a JSON object: {path}")
    return [Person(person, str(path)) for person in data]


def spec_layout(spec: DesignSpec) -> str:
    """Return the selected layout name."""
    return _required_string(spec._data, "layout", "Design Spec")


def spec_theme(spec: DesignSpec) -> str:
    """Return the selected theme name."""
    return _required_string(spec._data, "theme", "Design Spec")


def spec_logos(spec: DesignSpec) -> tuple[str, ...]:
    """Return the requested logo names."""
    logos = spec._data.get("logos", [])
    if not isinstance(logos, list) or not all(isinstance(logo, str) for logo in logos):
        raise ValueError("Design Spec field 'logos' must be an array of strings")
    return tuple(logos)


def canvas_geometry(spec: DesignSpec) -> tuple[float, float, float, float, float, float]:
    """Return canvas, trim, and safe-area dimensions in millimetres."""
    card = spec._data.get("card")
    if not isinstance(card, dict):
        raise ValueError("Design Spec field 'card' must be an object")
    width = _positive_number(card, "width_mm")
    height = _positive_number(card, "height_mm")
    bleed = _nonnegative_number(card, "bleed_mm")
    safe = _nonnegative_number(card, "safe_mm")
    return width + 2 * bleed, height + 2 * bleed, bleed, bleed, width, height


def safe_inset(spec: DesignSpec) -> float:
    """Return the safe margin inside the trim box."""
    card = spec._data.get("card")
    if not isinstance(card, dict):
        raise ValueError("Design Spec field 'card' must be an object")
    return _nonnegative_number(card, "safe_mm")


def requested_dpi(spec: DesignSpec) -> int:
    """Return the requested export DPI, defaulting to 300."""
    value = spec._data.get("dpi", 300)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("Design Spec field 'dpi' must be a positive integer")
    return value


def event_value(spec: DesignSpec, field: str) -> str | None:
    """Return an event string without inventing missing event details."""
    event = spec._data.get("event")
    if not isinstance(event, dict):
        raise ValueError("Design Spec field 'event' must be an object")
    value = event.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"Design Spec field 'event.{field}' must be a string or null")
    return value


def person_value(person: Person, field: str) -> str | None:
    """Return an optional string value from a normalized person."""
    value = person._data.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"Person field {field!r} must be a string or null")
    return value


def person_id(person: Person) -> str | None:
    """Return a person's optional identifier without exposing the source JSON shape."""
    return person_value(person, "id")


def person_photo_path(person: Person) -> Path | None:
    """Resolve the optional sample photo under the people-data directory."""
    photo = person_value(person, "photo")
    if not photo:
        return None
    source = Path(person._source_file).resolve() if person._source_file else PEOPLE_PATH.resolve()
    data_root = source.parent.resolve()
    path = (data_root / photo).resolve()
    if path != data_root and data_root not in path.parents:
        raise ValueError(f"Person photo path must remain under {data_root}: {photo}")
    return path


def attendance_url_base(spec: DesignSpec) -> str | None:
    """Return the optional attendance URL prefix from the temporary spec."""
    value = spec._data.get("attendance_url_base")
    if value is not None and not isinstance(value, str):
        raise ValueError("Design Spec field 'attendance_url_base' must be a string or null")
    return value


def person_role(person: Person) -> str:
    """Return and validate a person's role."""
    source = person._source_file or "person data"
    role = person._data.get("role")
    if not isinstance(role, str) or not role:
        raise ValueError(f"Person data is missing a role in {source}")
    if role not in ROLES:
        raise ValueError(f"Unknown role {role!r} in {source}; expected one of {', '.join(ROLES)}")
    return role


def with_choices(spec: DesignSpec, *, layout: str | None = None, theme: str | None = None) -> DesignSpec:
    """Return a spec copy with optional layout or theme selections replaced."""
    data = dict(spec._data)
    if layout is not None:
        data["layout"] = layout
    if theme is not None:
        data["theme"] = theme
    return DesignSpec(data)


def sample_person_for_role(role: str, people: list[Person]) -> Person:
    """Choose the first sample record matching a requested role."""
    if role not in ROLES:
        raise ValueError(f"Unknown role {role!r}; expected one of {', '.join(ROLES)}")
    for person in people:
        if person_role(person) == role:
            return person
    raise ValueError(f"No sample person found for role {role!r}")


def _required_string(data: dict[str, Any], field: str, source: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{source} field {field!r} must be a non-empty string")
    return value


def _positive_number(data: dict[str, Any], field: str) -> float:
    value = _number(data, field)
    if value <= 0:
        raise ValueError(f"Design Spec field 'card.{field}' must be greater than zero")
    return value


def _nonnegative_number(data: dict[str, Any], field: str) -> float:
    value = _number(data, field)
    if value < 0:
        raise ValueError(f"Design Spec field 'card.{field}' cannot be negative")
    return value


def _number(data: dict[str, Any], field: str) -> float:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Design Spec field 'card.{field}' must be a number")
    return float(value)
