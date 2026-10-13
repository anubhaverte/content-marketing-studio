"""List the available layouts and themes in the template library."""
from app.config import LAYOUTS, THEMES
from app.spec.loader import load_layout, load_theme
from app.spec.schema import Layout, Theme


def list_layouts() -> list[str]:
    """Return sorted names of all layout files in the template library."""
    if not LAYOUTS.exists():
        return []
    return sorted(f.stem for f in LAYOUTS.glob("*.json"))


def list_themes() -> list[str]:
    """Return sorted names of all theme files in the template library."""
    if not THEMES.exists():
        return []
    return sorted(f.stem for f in THEMES.glob("*.json"))


def get_layout(name: str) -> Layout:
    """Load and validate a layout by name from the template library."""
    return load_layout(LAYOUTS / f"{name}.json")


def get_theme(name: str) -> Theme:
    """Load and validate a theme by name from the template library."""
    return load_theme(THEMES / f"{name}.json")
