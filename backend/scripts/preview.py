"""Render one layout/theme/person to SVG, PNG, and PDF.

Run from backend/:
  python scripts/preview.py app/templates/layouts/classic.json app/templates/themes/clean_light.json
  python scripts/preview.py layout.json theme.json person.json output-directory
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import OUTPUT
from app.export.svg import save_svg
from app.render.svg_builder import build_svg
from app.spec.loader import SpecError, load_layout, load_theme, merge_design_spec
from app.spec.schema import Person


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4, 5):
        print(__doc__)
        return 2

    layout_path, theme_path = Path(argv[1]), Path(argv[2])
    person_path = Path(argv[3]) if len(argv) >= 4 else None
    output_dir = Path(argv[4]) if len(argv) == 5 else OUTPUT / "preview"
    try:
        layout = load_layout(layout_path)
        theme = load_theme(theme_path)
        person = _load_person(person_path) if person_path else Person(name="Preview Person")
        spec = merge_design_spec(layout, theme)
        svg = build_svg(spec, person)
    except (SpecError, OSError, ValueError) as error:
        print(f"PROBLEM\n{error}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    svg_path = save_svg(svg, output_dir / "preview.svg")
    try:
        from app.export.pdf import svg_to_pdf
        from app.export.png import svg_to_png

        png_path = svg_to_png(svg, output_dir / "preview.png", dpi=spec.print_settings.dpi)
        pdf_path = svg_to_pdf(svg, output_dir / "preview.pdf")
    except (ImportError, OSError, RuntimeError) as error:
        print(f"SVG saved: {svg_path}")
        print(f"PNG/PDF export failed: {error}")
        return 1

    print(f"SVG: {svg_path}")
    print(f"PNG: {png_path}")
    print(f"PDF: {pdf_path}")
    return 0


def _load_person(path: Path) -> Person:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read person data {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"Person data must be one JSON object: {path}")
    return Person.model_validate(value)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
