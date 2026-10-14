"""Load layout and theme JSON files with actionable errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAYOUTS_DIR = PROJECT_ROOT / "templates" / "layouts"
THEMES_DIR = PROJECT_ROOT / "templates" / "themes"


def load_layout(name: str, layouts_dir: Path = LAYOUTS_DIR) -> dict[str, Any]:
    """Load a named layout JSON file."""
    return _load_json(name, layouts_dir, "layout")


def load_theme(name: str, themes_dir: Path = THEMES_DIR) -> dict[str, Any]:
    """Load a named theme JSON file."""
    return _load_json(name, themes_dir, "theme")


def _load_json(name: str, directory: Path, kind: str) -> dict[str, Any]:
    path = directory / f"{name}.json"
    if not path.is_file():
        raise ValueError(f"Unknown {kind} {name!r}; expected file: {path}")
    try:
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read {kind} file {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"{kind.title()} file must contain a JSON object: {path}")
    data["_source_file"] = str(path)
    return data
