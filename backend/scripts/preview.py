"""Validate a layout and a theme file.

Usage (from backend/):
  python scripts/preview.py app/templates/layouts/classic.json app/templates/themes/clean_light.json

For now this only CHECKS the two files and prints either OK or a list of problems.
TODO (Phase 2): also render preview.png so the design can be seen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.spec.loader import SpecError, load_layout, load_theme


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    layout_path, theme_path = Path(argv[1]), Path(argv[2])
    ok = True
    try:
        layout = load_layout(layout_path)
        print(f"OK  layout '{layout.name}': {len(layout.elements)} elements, page {layout.page.width_mm} x {layout.page.height_mm} mm")
    except SpecError as e:
        ok = False
        print(f"PROBLEM\n{e}")
    try:
        theme = load_theme(theme_path)
        print(f"OK  theme '{theme.name}': fonts {theme.fonts.heading} / {theme.fonts.body}, roles {', '.join(theme.role_colors)}")
    except SpecError as e:
        ok = False
        print(f"PROBLEM\n{e}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
