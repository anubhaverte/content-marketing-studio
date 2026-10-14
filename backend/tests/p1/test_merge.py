"""Tests for spec merging: layout + theme + brand kit -> DesignSpec."""
import copy
from pathlib import Path
import pytest

from app.assets.brand_kit import load_brand_kit
from app.generator.library import get_layout, get_theme
from app.spec.loader import merge_design_spec, SpecError
from app.spec.paths import asset_path
from app.spec.schema import BrandKit, LogoEl


def test_merge_classic_clean_light():
    """Merging classic layout and clean_light theme produces a valid DesignSpec."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")
    spec = merge_design_spec(layout, theme)

    assert spec.layout_name == "classic"
    assert spec.theme_name == "clean_light"

    # Canvas and trim dimensions
    assert spec.page.width_mm == 54
    assert spec.page.height_mm == 86
    assert spec.page.canvas_w_mm == 60
    assert spec.page.canvas_h_mm == 92
    assert spec.page.bleed_mm == 3
    assert spec.page.safe_mm == 4

    # Safe zone coordinates
    assert spec.page.bleed_mm + spec.page.safe_mm == 7
    assert spec.page.canvas_w_mm - (spec.page.bleed_mm + spec.page.safe_mm) == 53
    assert spec.page.canvas_h_mm - (spec.page.bleed_mm + spec.page.safe_mm) == 85

    # Check elements and theme
    assert len(spec.elements) == len(layout.elements)
    assert spec.theme.colors.primary == theme.colors.primary
    assert spec.theme.colors.background == theme.colors.background


def test_merge_immutability():
    """Merging does not mutate the original layout or theme objects."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")

    layout_dump_before = layout.model_dump()
    theme_dump_before = theme.model_dump()

    _ = merge_design_spec(layout, theme)

    assert layout.model_dump() == layout_dump_before
    assert theme.model_dump() == theme_dump_before


def test_merge_brand_primary_override():
    """Brand kit primary color overrides the theme's primary color."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")

    custom_brand = BrandKit(
        primary_color="#123456",
        logos={
            "acm_nitsurat": "assets/logos/acm_nitsurat.svg",
            "svnit": "assets/logos/svnit.svg",
        },
    )

    spec = merge_design_spec(layout, theme, brand=custom_brand)

    assert spec.theme.colors.primary == "#123456"
    assert theme.colors.primary != "#123456"


def test_merge_unknown_logo_src_raises():
    """A layout referencing a logo missing from brand.logos raises SpecError."""
    layout = get_layout("classic")
    theme = get_theme("clean_light")

    # Add an element with an unknown logo ID
    layout_with_bad_logo = layout.model_copy(deep=True)
    layout_with_bad_logo.elements.append(
        LogoEl(type="logo", src="non_existent_logo", x=10, y=10, w=15)
    )

    with pytest.raises(SpecError, match="not in the brand kit"):
        merge_design_spec(layout_with_bad_logo, theme)


def test_brand_kit_asset_paths_resolve():
    """Default brand kit logo paths are repo-relative and resolve to existing files."""
    brand = load_brand_kit()
    for logo_id, rel_path in brand.logos.items():
        resolved = asset_path(rel_path)
        assert resolved.exists(), f"Logo file for '{logo_id}' not found at {resolved}"
        assert resolved.is_file()
