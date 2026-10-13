"""Load and validate layout and theme JSON files with friendly error messages."""
import json
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.assets.brand_kit import load_brand_kit
from app.spec.schema import (
    BrandKit,
    DesignSpec,
    EventInfo,
    Layout,
    PrintSettings,
    Theme,
)


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


def merge_design_spec(
    layout: Layout,
    theme: Theme,
    brand: Optional[BrandKit] = None,
    event: Optional[EventInfo] = None,
    print_settings: Optional[PrintSettings] = None,
) -> DesignSpec:
    """Combine a layout, theme, brand kit, event info, and print settings into one DesignSpec.

    Never mutates input objects. Brand colors override theme primary/secondary colors.
    Validates that all logo elements reference a logo ID present in brand.logos.
    """
    layout_copy = layout.model_copy(deep=True)
    theme_copy = theme.model_copy(deep=True)
    brand_copy = brand.model_copy(deep=True) if brand is not None else load_brand_kit()
    event_copy = event.model_copy(deep=True) if event is not None else EventInfo()
    settings_copy = print_settings.model_copy(deep=True) if print_settings is not None else PrintSettings()

    # Override theme primary/secondary colors if defined in brand kit
    updated_colors = theme_copy.colors.model_dump()
    if brand_copy.primary_color is not None:
        updated_colors["primary"] = brand_copy.primary_color
    if brand_copy.secondary_color is not None:
        updated_colors["secondary"] = brand_copy.secondary_color
    theme_copy = theme_copy.model_copy(update={"colors": type(theme_copy.colors)(**updated_colors)})

    # Validate that every logo element's src exists in brand.logos
    for el in layout_copy.elements:
        if getattr(el, "type", None) == "logo":
            logo_src = getattr(el, "src", "")
            if logo_src not in brand_copy.logos:
                raise SpecError(f"logo '{logo_src}' used in layout '{layout_copy.name}' is not in the brand kit")

    return DesignSpec(
        layout_name=layout_copy.name,
        theme_name=theme_copy.name,
        page=layout_copy.page.model_copy(deep=True),
        theme=theme_copy,
        elements=layout_copy.elements,
        brand=brand_copy,
        event=event_copy,
        print_settings=settings_copy,
    )
