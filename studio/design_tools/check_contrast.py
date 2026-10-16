"""Check theme text contrast and suggest a nearby passing text color."""

import json
import sys
from pathlib import Path
from typing import Any

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import (
    ALLOWED_ROLES,
    MIN_CONTRAST_RATIO,
    THEMES_DIR,
    contrast_ratio,
    hex_to_rgb,
)


def _valid_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        return False
    try:
        hex_to_rgb(value)
    except ValueError:
        return False
    return True


def _rgb_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02X}{green:02X}{blue:02X}"


def _nearest_passing_text(text_color: str, background: str) -> tuple[str, float]:
    """Find the least RGB-distance shade or tint of the original text that passes."""
    original = hex_to_rgb(text_color)
    candidates = []
    for direction in ("darken", "lighten"):
        for step in range(1001):
            amount = step / 1000
            if direction == "darken":
                adjusted = tuple(round(channel * (1 - amount)) for channel in original)
            else:
                adjusted = tuple(
                    round(channel + (255 - channel) * amount) for channel in original
                )
            candidate = _rgb_hex(*adjusted)
            ratio = contrast_ratio(candidate, background)
            if ratio >= MIN_CONTRAST_RATIO:
                distance = sum((new - old) ** 2 for new, old in zip(adjusted, original))
                candidates.append((distance, candidate, ratio))
                break
    if not candidates:
        return "#000000 or #FFFFFF", 0.0
    _, candidate, ratio = min(candidates)
    return candidate, ratio


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

    print(f"\n{path.name} contrast ratios")
    print(f"{'Foreground on background':<34} {'Ratio':>8}  Result")
    pairs = []
    colors = theme.get("colors")
    if not isinstance(colors, dict):
        colors = {}
    text_color = colors.get("text")
    for name in ("background", "primary", "secondary"):
        pairs.append((f"text on {name}", text_color, colors.get(name)))
    pairs.append(("muted on background", colors.get("muted"), colors.get("background")))

    role_colors = theme.get("role_colors")
    if not isinstance(role_colors, dict):
        role_colors = {}
    for role in sorted(ALLOWED_ROLES):
        role_palette = role_colors.get(role)
        if not isinstance(role_palette, dict):
            role_palette = {}
        pairs.append(
            (
                f"{role} badge text",
                role_palette.get("text"),
                role_palette.get("background"),
            )
        )

    theme_passed = True
    for label, foreground, background in pairs:
        if not _valid_hex(foreground) or not _valid_hex(background):
            print(f"{label:<34} {'n/a':>8}  FAIL (missing or invalid hex color)")
            theme_passed = False
            continue
        ratio = contrast_ratio(foreground, background)
        passed = ratio >= MIN_CONTRAST_RATIO
        print(f"{label:<34} {ratio:>7.2f}:1  {'PASS' if passed else 'FAIL'}")
        if not passed:
            theme_passed = False
            suggestion, suggested_ratio = _nearest_passing_text(foreground, background)
            print(
                f"  Suggest text {suggestion} for {background}; "
                f"contrast {suggested_ratio:.2f}:1"
            )

    print(
        f"{'PASS' if theme_passed else 'FAIL'} {path.name}: "
        f"contrast minimum {MIN_CONTRAST_RATIO:.1f}:1"
    )
    return theme_passed


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
