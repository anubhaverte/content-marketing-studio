"""Render one hardcoded, vector Incursion ID card and export it."""

from __future__ import annotations

import base64
import os
import sys
import warnings
from pathlib import Path
from typing import NamedTuple
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from PIL import Image, ImageFont


# Sample data, colors, and sizes. SVG coordinates use millimetres (1 unit = 1 mm).
SAMPLE_NAME = "Riya Shah"
SAMPLE_INITIALS = "RS"
EVENT_PLACEHOLDER = "EVENT NAME"
ROLE_LABEL = "PARTICIPANT"
ROLE_COLOR = "#4169e1"
CARD_COLOR = "#ffffff"
BLEED_COLOR = "#e8edf5"
PHOTO_COLOR = "#d5d9df"
TEXT_COLOR = "#172238"
LOGO_PLACEHOLDER_COLOR = "#4b5563"

TRIM_WIDTH_MM = 54
TRIM_HEIGHT_MM = 86
BLEED_MM = 3
CANVAS_WIDTH_MM = 60
CANVAS_HEIGHT_MM = 92
SAFE_MARGIN_MM = 3
SAFE_LEFT_MM = BLEED_MM + SAFE_MARGIN_MM
SAFE_RIGHT_MM = CANVAS_WIDTH_MM - SAFE_LEFT_MM
SAFE_TOP_MM = BLEED_MM + SAFE_MARGIN_MM
SAFE_BOTTOM_MM = CANVAS_HEIGHT_MM - SAFE_TOP_MM
LOGO_HEIGHT_MM = 8
LOGO_SLOT_WIDTH_MM = 21
LOGO_LEFT_X_MM = SAFE_LEFT_MM
LOGO_RIGHT_X_MM = SAFE_RIGHT_MM - LOGO_SLOT_WIDTH_MM
LOGO_Y_MM = SAFE_TOP_MM
EVENT_Y_MM = 18
EVENT_HEIGHT_MM = 13
PHOTO_DIAMETER_MM = 22
PHOTO_CENTER_X_MM = CANVAS_WIDTH_MM / 2
PHOTO_CENTER_Y_MM = 44
NAME_BASE_SIZE_MM = 5
NAME_LONG_THRESHOLD = 15
NAME_GLYPH_WIDTH_FACTOR = 1.05
EVENT_FONT_SIZE_MM = 3.4
ROLE_FONT_SIZE_MM = 3.2
OUTPUT_DPI = 300
OUTPUT_WIDTH_PX = 709
OUTPUT_HEIGHT_PX = 1087

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "sample_output"


class LogoResult(NamedTuple):
    """Markup and status for a real logo or a placeholder."""

    markup: str
    status: str


def select_font() -> tuple[str, str]:
    """Choose the first installed font from the supported fallback list."""
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    local_fonts = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"
    candidates = (
        ("Arial", (windows / "arial.ttf", local_fonts / "arial.ttf")),
        ("Segoe UI", (windows / "segoeui.ttf", local_fonts / "segoeui.ttf")),
        ("DejaVu Sans", (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),)),
    )
    for family, paths in candidates:
        for path in paths:
            if path.is_file():
                try:
                    ImageFont.truetype(str(path), 12)
                    return family, str(path)
                except OSError:
                    continue
    return "sans-serif", "system fallback (font file not detected)"


def logo_aspect_ratio(path: Path) -> float:
    """Read a PNG's pixel ratio or an SVG's viewBox ratio."""
    if path.suffix.lower() == ".png":
        with Image.open(path) as image:
            width, height = image.size
    elif path.suffix.lower() == ".svg":
        root = ElementTree.parse(path).getroot()
        view_box = root.get("viewBox") or root.get("viewbox")
        if not view_box:
            raise ValueError(f"SVG logo must have a viewBox: {path}")
        values = [float(value) for value in view_box.replace(",", " ").split()]
        if len(values) != 4:
            raise ValueError(f"SVG viewBox must contain four numbers: {path}")
        _, _, width, height = values
    else:
        raise ValueError(f"Logo must be SVG or PNG: {path}")
    if width <= 0 or height <= 0:
        raise ValueError(f"Logo dimensions must be positive: {path}")
    return width / height


def find_logo(name: str) -> Path | None:
    """Find an SVG logo, falling back to a PNG, under assets/."""
    for suffix in (".svg", ".png"):
        path = ASSETS_DIR / f"{name}{suffix}"
        if path.is_file():
            return path
    return None


def logo_markup(name: str, label: str, slot_x: float) -> LogoResult:
    """Make a logo data-URI image or a visible, warned placeholder."""
    path = find_logo(name)
    if path is None:
        warnings.warn(f"Missing logo: assets/{name}.svg or assets/{name}.png")
        print(f"WARNING: {label} logo missing; drew 'LOGO MISSING: {name}'.", file=sys.stderr)
        placeholder = (
            f'<g id="logo-{name}" data-logo-status="placeholder">'
            f'<rect x="{slot_x}" y="{LOGO_Y_MM}" width="{LOGO_SLOT_WIDTH_MM}" height="{LOGO_HEIGHT_MM}" '
            f'rx="0.6" fill="#fff" stroke="{LOGO_PLACEHOLDER_COLOR}" stroke-dasharray="0.8 0.5"/>'
            f'<text x="{slot_x + LOGO_SLOT_WIDTH_MM / 2}" y="{LOGO_Y_MM + 4.7}" text-anchor="middle" '
            f'font-size="1.45" fill="{LOGO_PLACEHOLDER_COLOR}">LOGO MISSING: {escape(name)}</text></g>'
        )
        return LogoResult(placeholder, "placeholder")

    ratio = logo_aspect_ratio(path)
    scale = min(1.0, LOGO_SLOT_WIDTH_MM / (ratio * LOGO_HEIGHT_MM))
    width = ratio * LOGO_HEIGHT_MM * scale
    height = LOGO_HEIGHT_MM * scale
    x = slot_x + (LOGO_SLOT_WIDTH_MM - width) / 2
    y = LOGO_Y_MM + (LOGO_HEIGHT_MM - height) / 2
    media_type = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    markup = (
        f'<image id="logo-{name}" data-logo-status="embedded" x="{x:.4f}" y="{y:.4f}" '
        f'width="{width:.4f}" height="{height:.4f}" preserveAspectRatio="xMidYMid meet" '
        f'href="data:{media_type};base64,{encoded}"/>'
    )
    print(f"Embedded {label} logo from {path.relative_to(PROJECT_ROOT)} without stretching.")
    return LogoResult(markup, "embedded")


def name_font_size(name: str) -> float:
    """Reduce long names with a temporary character-count width estimate."""
    if len(name) <= NAME_LONG_THRESHOLD:
        return NAME_BASE_SIZE_MM
    safe_width = SAFE_RIGHT_MM - SAFE_LEFT_MM
    return min(NAME_BASE_SIZE_MM, safe_width / (len(name) * NAME_GLYPH_WIDTH_FACTOR))


def build_svg(font_family: str) -> str:
    """Build the single portrait card with full-bleed background blocks."""
    acm = logo_markup("acm", "ACM NIT Surat", LOGO_LEFT_X_MM)
    svnit = logo_markup("svnit", "SVNIT", LOGO_RIGHT_X_MM)
    font_stack = escape(f'"{font_family}", "Segoe UI", "DejaVu Sans", sans-serif', {'"': "&quot;"})
    name_size = name_font_size(SAMPLE_NAME)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  width="60mm" height="92mm" viewBox="0 0 60 92"
  data-logo-acm="{acm.status}" data-logo-svnit="{svnit.status}" data-trim-box="3 3 54 86">
  <rect x="0" y="0" width="60" height="92" fill="{BLEED_COLOR}"/>
  <rect x="3" y="3" width="54" height="86" fill="{CARD_COLOR}"/>
  {acm.markup}
  {svnit.markup}
  <rect x="0" y="{EVENT_Y_MM}" width="60" height="{EVENT_HEIGHT_MM}" fill="{ROLE_COLOR}"/>
  <text x="30" y="{EVENT_Y_MM + 8.5}" text-anchor="middle" font-family="{font_stack}"
    font-size="{EVENT_FONT_SIZE_MM}" font-weight="700" fill="#fff">{escape(EVENT_PLACEHOLDER)}</text>
  <circle cx="{PHOTO_CENTER_X_MM}" cy="{PHOTO_CENTER_Y_MM}" r="{PHOTO_DIAMETER_MM / 2}" fill="{PHOTO_COLOR}"/>
  <text x="{PHOTO_CENTER_X_MM}" y="{PHOTO_CENTER_Y_MM + 1.5}" text-anchor="middle" font-family="{font_stack}"
    font-size="5" font-weight="700" fill="#fff">{escape(SAMPLE_INITIALS)}</text>
  <text x="30" y="66" text-anchor="middle" font-family="{font_stack}" font-size="{name_size:.3f}"
    font-weight="700" fill="{TEXT_COLOR}">{escape(SAMPLE_NAME)}</text>
  <rect x="0" y="74" width="60" height="18" fill="{ROLE_COLOR}"/>
  <text x="30" y="81" text-anchor="middle" font-family="{font_stack}" font-size="{ROLE_FONT_SIZE_MM}"
    font-weight="700" fill="#fff">{escape(ROLE_LABEL)}</text>
</svg>'''


def export_card() -> None:
    """Write card.svg, card.pdf, and card.png using CairoSVG."""
    font_family, font_path = select_font()
    print(f"Selected installed font: {font_family} ({font_path}); SVG fallbacks: Segoe UI, DejaVu Sans, sans-serif.")
    svg_path = OUTPUT_DIR / "card.svg"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(build_svg(font_family), encoding="utf-8")
    try:
        import cairosvg
    except (ImportError, OSError) as error:
        raise RuntimeError(
            "CairoSVG could not load its Cairo native library. Follow the Windows install steps in README.md. "
            f"Original error: {error}"
        ) from error
    cairosvg.svg2pdf(url=str(svg_path), write_to=str(OUTPUT_DIR / "card.pdf"))
    cairosvg.svg2png(
        url=str(svg_path), write_to=str(OUTPUT_DIR / "card.png"), dpi=OUTPUT_DPI,
        output_width=OUTPUT_WIDTH_PX, output_height=OUTPUT_HEIGHT_PX,
    )
    print(f"Wrote {OUTPUT_DIR / 'card.svg'}, card.pdf, and card.png.")


def main() -> int:
    """Run the one-card export and report actionable errors."""
    try:
        export_card()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())