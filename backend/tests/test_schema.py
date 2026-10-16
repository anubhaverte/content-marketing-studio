"""Schema rules: good files load, bad files are rejected with clear messages."""
import copy
import json

import pytest

from app.brief.schema import Brief
from app.config import LAYOUTS, THEMES
from app.spec.loader import SpecError, load_layout, load_theme

STARTER_LAYOUT = json.loads((LAYOUTS / "classic.json").read_text(encoding="utf-8"))
STARTER_THEME = json.loads((THEMES / "clean_light.json").read_text(encoding="utf-8"))


def layout_error(tmp_path, data) -> str:
    """Write a layout dict to a file, load it, and return the SpecError message."""
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SpecError) as info:
        load_layout(path)
    return str(info.value)


def theme_error(tmp_path, data) -> str:
    path = tmp_path / "theme.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SpecError) as info:
        load_theme(path)
    return str(info.value)


def test_starter_files_load():
    assert load_layout(LAYOUTS / "classic.json").name == "classic"
    assert load_theme(THEMES / "clean_light.json").name == "clean_light"


def test_hex_color_in_layout_is_rejected(tmp_path):
    data = copy.deepcopy(STARTER_LAYOUT)
    data["elements"][0]["fill"] = "#FFFFFF"
    msg = layout_error(tmp_path, data)
    assert "elements.0.fill" in msg
    assert "theme token" in msg


def test_unknown_property_is_rejected(tmp_path):
    data = copy.deepcopy(STARTER_LAYOUT)
    data["elements"][1]["dsh"] = [2, 1]
    msg = layout_error(tmp_path, data)
    assert "elements.1.dsh" in msg
    assert "unknown property" in msg


@pytest.mark.parametrize("extra", [{"field": "name", "value": "Hello"}, {}])
def test_text_needs_exactly_one_of_field_or_value(tmp_path, extra):
    data = copy.deepcopy(STARTER_LAYOUT)
    data["elements"].append({"type": "text", "x": 7, "y": 10, "w": 20, **extra})
    msg = layout_error(tmp_path, data)
    assert f"elements.{len(data['elements']) - 1}" in msg
    assert "exactly one of 'field' or 'value'" in msg


def test_qr_must_be_square(tmp_path):
    data = copy.deepcopy(STARTER_LAYOUT)
    data["elements"].append({"type": "qr", "x": 10, "y": 10, "w": 12, "h": 10})
    msg = layout_error(tmp_path, data)
    assert "square" in msg


def test_min_font_larger_than_max_font_is_rejected(tmp_path):
    data = copy.deepcopy(STARTER_LAYOUT)
    data["elements"].append({"type": "text", "value": "Hi", "x": 7, "y": 10, "w": 20, "min_font": 20, "max_font": 10})
    msg = layout_error(tmp_path, data)
    assert "min_font" in msg


def test_unknown_element_type_is_rejected(tmp_path):
    data = copy.deepcopy(STARTER_LAYOUT)
    data["elements"].append({"type": "triangle", "x": 1, "y": 1})
    msg = layout_error(tmp_path, data)
    assert "elements." in msg


def test_gradient_fill_with_tokens_is_valid(tmp_path):
    from app.spec.schema import Layout

    data = copy.deepcopy(STARTER_LAYOUT)
    data["elements"][1]["fill"] = {"gradient": "linear", "angle": 135, "stops": [[0, "primary"], [1, "background"]]}
    Layout.model_validate(data)  # should not raise


def test_theme_missing_a_role_color_is_rejected(tmp_path):
    data = copy.deepcopy(STARTER_THEME)
    del data["role_colors"]["mentor"]
    msg = theme_error(tmp_path, data)
    assert "mentor" in msg


def test_theme_needs_hex_colors(tmp_path):
    data = copy.deepcopy(STARTER_THEME)
    data["colors"]["primary"] = "blue"
    msg = theme_error(tmp_path, data)
    assert "colors.primary" in msg
    assert "hex" in msg


def test_missing_file_gives_friendly_error(tmp_path):
    with pytest.raises(SpecError):
        load_layout(tmp_path / "nope.json")


def test_invalid_json_gives_friendly_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(SpecError):
        load_layout(bad)


def test_brief_with_everything_unknown_is_valid():
    brief = Brief()
    assert brief.design_type == "id_card"
    assert brief.event_name is None and brief.roles is None and brief.lanyard_hole is None
