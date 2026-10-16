"""Check whether theme roles remain distinguishable in grayscale printing."""

import json
import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import ALLOWED_ROLES, THEMES_DIR, hex_to_rgb, relative_luminance

LUMINANCE_WARNING_THRESHOLD = 0.15


def _valid_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        return False
    try:
        hex_to_rgb(value)
    except ValueError:
        return False
    return True


def _load_theme(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open(encoding="utf-8") as theme_file:
            theme = json.load(theme_file)
    except (OSError, json.JSONDecodeError) as error:
        return None, str(error)
    if not isinstance(theme, dict):
        return None, "top-level JSON value must be an object"
    return theme, None


def check_theme(path: Path) -> bool:
    theme, error = _load_theme(path)
    if error is not None:
        print(f"FAIL {path.name}: invalid theme JSON: {error}")
        return False

    role_colors = theme.get("role_colors")
    role_styles = theme.get("role_style")
    if not isinstance(role_colors, dict) or not isinstance(role_styles, dict):
        print(f"FAIL {path.name}: role_colors and role_style must be objects")
        return False

    luminances = {}
    styles = {}
    valid = True
    for role in sorted(ALLOWED_ROLES):
        palette = role_colors.get(role)
        style = role_styles.get(role)
        if not isinstance(palette, dict) or not _valid_hex(palette.get("background")):
            print(f"FAIL {path.name} / role '{role}': missing valid background color")
            valid = False
            continue
        if not isinstance(style, dict):
            print(f"FAIL {path.name} / role '{role}': missing role_style object")
            valid = False
            continue
        luminances[role] = relative_luminance(*hex_to_rgb(palette["background"]))
        styles[role] = (
            style.get("badge_shape"),
            style.get("badge_border"),
            style.get("label"),
        )
        print(
            f"PASS {path.name} / role '{role}': grayscale luminance "
            f"{luminances[role] * 100:.1f}%"
        )

    for first_index, first_role in enumerate(sorted(luminances)):
        for second_role in sorted(luminances)[first_index + 1 :]:
            difference = abs(luminances[first_role] - luminances[second_role])
            same_style = styles[first_role] == styles[second_role]
            if difference < LUMINANCE_WARNING_THRESHOLD and same_style:
                print(
                    f"WARN {path.name} / roles '{first_role}' and '{second_role}': "
                    f"luminance differs by {difference * 100:.1f}% and role styles match"
                )
            else:
                reason = (
                    "role styles differ"
                    if not same_style
                    else f"luminance differs by {difference * 100:.1f}%"
                )
                print(
                    f"PASS {path.name} / roles '{first_role}' and '{second_role}': "
                    f"grayscale distinction ({reason})"
                )
    return valid


def main() -> int:
    theme_paths = sorted(THEMES_DIR.glob("*.json"))
    if not theme_paths:
        print(f"FAIL themes: no JSON files found in {THEMES_DIR}")
        return 1
    passed = True
    for theme_path in theme_paths:
        if not check_theme(theme_path):
            passed = False
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
