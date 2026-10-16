"""Temporary stand-in preview using CairoSVG; replace with renderer implementation."""

import sys
import warnings
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import SAMPLE_DATA_DIR
from studio.design_tools.render_card import (
    load_attendees,
    load_layout_theme,
    render_png,
    render_svg,
)


def main() -> None:
    attendees = load_attendees()
    person = next(
        attendee
        for attendee in attendees
        if attendee["full_name"] == "Aarav Sharma" and attendee["photo"]
    )
    layout, theme = load_layout_theme("classic", "clean_light")
    svg = render_svg(layout, theme, person)
    svg_path = SAMPLE_DATA_DIR / "preview_local.svg"
    png_path = SAMPLE_DATA_DIR / "preview_local.png"
    svg_path.write_text(svg, encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        png_path.write_bytes(render_png(layout, theme, person))
    print("TEMPORARY STAND-IN preview (classic + clean_light)")
    print(f"SVG: {svg_path}")
    print(f"PNG: {png_path}")


if __name__ == "__main__":
    main()
