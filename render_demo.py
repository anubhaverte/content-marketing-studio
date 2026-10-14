"""Render every sample person to SVG, PDF, and PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from render import spec_adapter
from render.renderer import render_card


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "sample_output" / "phase2"
OUTPUT_DPI = 300
OUTPUT_WIDTH_PX = 709
OUTPUT_HEIGHT_PX = 1087


def main() -> int:
    """Render all bundled people with the selected layout and theme."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", default="classic", help="layout name (default: classic)")
    parser.add_argument("--theme", default="blue", help="theme name (default: blue)")
    args = parser.parse_args()

    try:
        spec = spec_adapter.load_design_spec()
        spec = spec_adapter.with_choices(spec, layout=args.layout, theme=args.theme)
        people = spec_adapter.load_people()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            import cairosvg
        except (ImportError, OSError) as error:
            raise RuntimeError(
                "CairoSVG could not load its Cairo native library. Follow the Windows Cairo setup in README.md. "
                f"Original error: {error}"
            ) from error

        for index, person in enumerate(people, start=1):
            name = spec_adapter.person_value(person, "name") or f"person-{index}"
            role = spec_adapter.person_role(person)
            safe_name = "".join(char.lower() if char.isalnum() else "-" for char in name).strip("-")
            stem = f"{index:02d}-{safe_name}-{role}"
            svg_path = OUTPUT_DIR / f"{stem}.svg"
            pdf_path = OUTPUT_DIR / f"{stem}.pdf"
            png_path = OUTPUT_DIR / f"{stem}.png"
            svg = render_card(spec, person)
            svg_path.write_text(svg, encoding="utf-8")
            cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=str(pdf_path))
            cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                write_to=str(png_path),
                dpi=OUTPUT_DPI,
                output_width=OUTPUT_WIDTH_PX,
                output_height=OUTPUT_HEIGHT_PX,
            )
            print(f"Wrote {svg_path}, {pdf_path}, and {png_path}")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
