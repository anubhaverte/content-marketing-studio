"""Load and validate layout and theme JSON files with friendly error messages."""
import json
from pathlib import Path

from pydantic import ValidationError

from app.spec.schema import DesignSpec, Layout, Theme


class SpecError(Exception):
    """Raised when a JSON file is missing, not valid JSON, or breaks the schema."""


ELEMENT_TYPES = {"rect", "line", "circle", "text", "photo", "logo", "role_badge", "qr", "svg_asset"}


def _clean_path(loc: tuple) -> str:
    """Build 'elements.3.fill' from Pydantic's location, dropping the internal union tags."""
    parts = []
    for i, p in enumerate(loc):
        prev = loc[i - 1] if i > 0 else None
        if isinstance(p, str) and isinstance(prev, int) and p in ELEMENT_TYPES:
            continue  # element type tag after the list index
        if p in ("token", "gradient") and prev == "fill":
            continue  # fill union tag
        parts.append(str(p))
    return ".".join(parts) or "(whole file)"


def _format_errors(err: ValidationError, source: str) -> str:
    """Turn Pydantic errors into lines like 'elements.3.fill: message'."""
    lines = [f"{source} has {err.error_count()} problem(s):"]
    for e in err.errors():
        path = _clean_path(e["loc"])
        msg = e["msg"].removeprefix("Value error, ")
        if e["type"] == "extra_forbidden":
            msg = "unknown property (check the spelling)"
        lines.append(f"  - {path}: {msg}")
    return "\n".join(lines)


def _read_json(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise SpecError(f"File not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SpecError(f"{path.name} is not valid JSON: {e}") from e


def load_layout(path: Path) -> Layout:
    """Read a layout JSON file and validate it."""
    data = _read_json(path)
    try:
        return Layout.model_validate(data)
    except ValidationError as e:
        raise SpecError(_format_errors(e, Path(path).name)) from e


def load_theme(path: Path) -> Theme:
    """Read a theme JSON file and validate it."""
    data = _read_json(path)
    try:
        return Theme.model_validate(data)
    except ValidationError as e:
        raise SpecError(_format_errors(e, Path(path).name)) from e


def merge_design_spec(layout: Layout, theme: Theme) -> DesignSpec:
    """Combine a layout, a theme, the brand kit and event info into one DesignSpec.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: merge layout + theme + brand kit + event into a DesignSpec")
