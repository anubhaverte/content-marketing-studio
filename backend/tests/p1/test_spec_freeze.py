"""Tests for Design Spec schema freeze and additive model changes."""
import pytest
from pydantic import ValidationError

from app.config import LAYOUTS, THEMES
from app.spec.constants import SCHEMA_VERSION
from app.spec.loader import load_layout, load_theme
from app.spec.schema import (
    BrandKit,
    DesignSpec,
    Layout,
    PageSpec,
    Person,
    PrintSettings,
    RectEl,
    TextEl,
    Theme,
)


def test_schema_version_default():
    assert SCHEMA_VERSION == "1.0"
    layout = load_layout(LAYOUTS / "classic.json")
    theme = load_theme(THEMES / "clean_light.json")
    brand = BrandKit(logos={"acm_nitsurat": "assets/logos/acm_nitsurat.svg", "svnit": "assets/logos/svnit.svg"})

    spec = DesignSpec(
        layout_name=layout.name,
        theme_name=theme.name,
        page=layout.page,
        theme=theme,
        elements=layout.elements,
        brand=brand,
    )
    assert spec.schema_version == "1.0"


def test_duplicate_element_ids_rejected_with_name():
    el1 = RectEl(type="rect", id="box_one", x=0, y=0, w=10, h=10)
    el2 = RectEl(type="rect", id="box_one", x=5, y=5, w=20, h=20)

    with pytest.raises(ValidationError) as exc_info:
        Layout(name="dup_test", page=PageSpec(), elements=[el1, el2])
    assert "duplicate element id 'box_one'" in str(exc_info.value)


def test_element_without_id_is_fine():
    el1 = RectEl(type="rect", id=None, x=0, y=0, w=10, h=10)
    el2 = RectEl(type="rect", id=None, x=5, y=5, w=20, h=20)
    layout = Layout(name="no_ids", page=PageSpec(), elements=[el1, el2])
    assert len(layout.elements) == 2


def test_print_settings_defaults_and_validation():
    ps = PrintSettings()
    assert ps.dpi == 300
    assert ps.include_bleed is True
    assert ps.crop_marks is False
    assert ps.color_mode == "rgb"

    # 150, 300, 600 allowed
    assert PrintSettings(dpi=150).dpi == 150
    assert PrintSettings(dpi=600).dpi == 600

    # dpi=200 rejected
    with pytest.raises(ValidationError) as exc:
        PrintSettings(dpi=200)
    assert "dpi must be one of 150, 300, 600" in str(exc.value)


def test_person_get_field_known_extra_none():
    p = Person(name="Alice", role="mentor", email="alice@example.com", extra={"department": "CSE", "year": "4"})
    # Known fields
    assert p.get_field("name") == "Alice"
    assert p.get_field("role") == "mentor"
    assert p.get_field("email") == "alice@example.com"
    # Extra fields
    assert p.get_field("department") == "CSE"
    assert p.get_field("year") == "4"
    # Unknown field
    assert p.get_field("nonexistent") is None


def test_starter_layout_and_theme_load_unchanged():
    layout = load_layout(LAYOUTS / "classic.json")
    theme = load_theme(THEMES / "clean_light.json")
    assert layout.name == "classic"
    assert theme.name == "clean_light"
    assert len(layout.elements) > 0


def test_text_element_with_custom_department_field():
    el = TextEl(type="text", field="department", x=10, y=20, w=30)
    assert el.field == "department"
    assert el.value is None
