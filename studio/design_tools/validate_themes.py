"""Validate theme JSON files for schema, contrast, and monochrome role styling."""

import json
import re
import sys
from pathlib import Path

_current_dir = Path(__file__).resolve().parent
_repo_root = _current_dir.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import ALLOWED_ROLES, THEMES_DIR, contrast_ratio

REQUIRED_COLORS = {
    "primary",
    "secondary",
    "background",
    "text",
    "muted",
    "accent",
    "role",
}
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
EXPECTED_ROLE_STYLES = {
    "participant": ("pill", "solid", "PARTICIPANT"),
    "organizer": ("shield", "double", "ORGANIZER"),
    "mentor": ("rect", "dashed", "MENTOR"),
}


def validate_theme(theme_path: Path) -> list[str]:
    errors = []
    try:
        with theme_path.open(encoding="utf-8") as theme_file:
            theme = json.load(theme_file)
    except (OSError, json.JSONDecodeError) as error:
        return [f"Cannot read theme JSON: {error}"]

    for key in ("id", "name", "colors", "fonts", "role_colors", "role_style"):
        if key not in theme:
            errors.append(f"Missing required top-level key: '{key}'")

    colors = theme.get("colors")
    if not isinstance(colors, dict):
        errors.append("'colors' must be an object")
        colors = {}
    for color_name in REQUIRED_COLORS:
        value = colors.get(color_name)
        if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
            errors.append(f"Color '{color_name}' must be a #RRGGBB hex value")

    fonts = theme.get("fonts")
    if not isinstance(fonts, dict):
        errors.append("'fonts' must be an object")
    else:
        for font_name in ("heading", "body"):
            font_path = fonts.get(font_name)
            if not isinstance(font_path, str) or not font_path.strip():
                errors.append(f"Font '{font_name}' must be a non-empty path")
            elif not font_path.replace("\\", "/").startswith("assets/fonts/"):
                errors.append(f"Font '{font_name}' must point inside assets/fonts/")

    role_colors = theme.get("role_colors")
    role_style = theme.get("role_style")
    if not isinstance(role_colors, dict):
        errors.append("'role_colors' must be an object")
        role_colors = {}
    if not isinstance(role_style, dict):
        errors.append("'role_style' must be an object")
        role_style = {}

    shapes = set()
    borders = set()
    labels = set()
    for role in ALLOWED_ROLES:
        colors_for_role = role_colors.get(role)
        if not isinstance(colors_for_role, dict):
            errors.append(f"Missing role_colors entry for '{role}'")
            continue

        role_background = colors_for_role.get("background")
        role_text = colors_for_role.get("text")
        for key, value in (("background", role_background), ("text", role_text)):
            if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
                errors.append(f"Role '{role}' {key} must be a #RRGGBB hex value")

        if (
            isinstance(role_background, str)
            and HEX_COLOR.fullmatch(role_background)
            and isinstance(role_text, str)
            and HEX_COLOR.fullmatch(role_text)
            and contrast_ratio(role_text, role_background) < 4.5
        ):
            errors.append(f"Role '{role}' badge text/background contrast is below 4.5:1")

        style = role_style.get(role)
        if not isinstance(style, dict):
            errors.append(f"Missing role_style entry for '{role}'")
            continue
        expected_shape, expected_border, expected_label = EXPECTED_ROLE_STYLES[role]
        shape = style.get("badge_shape")
        border = style.get("badge_border")
        label = style.get("label")
        if shape != expected_shape:
            errors.append(f"Role '{role}' badge_shape must be '{expected_shape}'")
        if border != expected_border:
            errors.append(f"Role '{role}' badge_border must be '{expected_border}'")
        if label != expected_label:
            errors.append(f"Role '{role}' label must be '{expected_label}'")
        if isinstance(shape, str):
            shapes.add(shape)
        if isinstance(border, str):
            borders.add(border)
        if isinstance(label, str):
            labels.add(label)

    if len(shapes) != len(ALLOWED_ROLES):
        errors.append("Each role must have a distinct badge shape for grayscale distinction")
    if len(borders) != len(ALLOWED_ROLES):
        errors.append("Each role must have a distinct badge border for grayscale distinction")
    if len(labels) != len(ALLOWED_ROLES):
        errors.append("Each role must have a distinct explicit label")

    background = colors.get("background")
    for color_name in ("text", "muted"):
        foreground = colors.get(color_name)
        if (
            isinstance(background, str)
            and HEX_COLOR.fullmatch(background)
            and isinstance(foreground, str)
            and HEX_COLOR.fullmatch(foreground)
            and contrast_ratio(foreground, background) < 4.5
        ):
            errors.append(f"'{color_name}' on 'background' contrast is below 4.5:1")

    return errors


def main() -> int:
    all_passed = True
    for theme_name in ("clean_light.json", "dark_tech.json", "bold_event.json"):
        theme_path = THEMES_DIR / theme_name
        errors = validate_theme(theme_path)
        if errors:
            all_passed = False
            print(f"FAILED: {theme_name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASSED: {theme_name}")

    if all_passed:
        print("\nAll 3 themes satisfy the schema and accessibility requirements.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
