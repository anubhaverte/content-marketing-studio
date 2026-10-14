"""Phase 0 toolchain proof: Jinja2 -> SVG -> CairoSVG -> PDF + PNG.

Run from backend/:  python scripts/hello_card.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so "app" can be imported

from jinja2 import Environment, FileSystemLoader

from app.config import LOGOS, OUTPUT
from app.export.pdf import svg_to_pdf
from app.export.png import svg_to_png
from app.export.svg import save_svg
from app.render.embed import file_to_data_uri
from app.spec.constants import MM_PER_PT

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "app" / "render" / "jinja"

# Hardcoded data and colors. Phase 2 replaces these with a layout + theme + real person data.
COLORS = {
    "background": "#FFFFFF",
    "primary": "#1F6FEB",
    "secondary": "#EAF1FD",
    "accent": "#38BDF8",
    "text": "#0B1220",
}
ROLE_COLORS = {"participant": "#1F6FEB", "organizer": "#D9480F", "mentor": "#2F9E44"}
FONT_FAMILY = "Poppins, Inter, DejaVu Sans, Arial, sans-serif"


def render_hello_svg(name: str, role: str, debug_guides: bool) -> str:
    """Fill the hello_card template and return SVG text."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    env.filters["pt_to_mm"] = lambda pt: round(pt * MM_PER_PT, 4)  # font sizes: pt -> mm
    template = env.get_template("hello_card.svg.j2")
    return template.render(
        colors=COLORS,
        font_family=FONT_FAMILY,
        name=name,
        role=role,
        role_color=ROLE_COLORS[role],
        debug_guides=debug_guides,
        logos={
            "acm_nitsurat": file_to_data_uri(LOGOS / "acm_nitsurat.svg"),
            "svnit": file_to_data_uri(LOGOS / "svnit.svg"),
        },
    )


def run(out_dir: Path = OUTPUT) -> dict:
    """Render the hello card and write .svg, .pdf and .png into out_dir."""
    svg = render_hello_svg("Priya Venkatakrishnan", "participant", debug_guides=True)
    return {
        "svg": save_svg(svg, out_dir / "hello_card.svg"),
        "pdf": svg_to_pdf(svg, out_dir / "hello_card.pdf"),
        "png": svg_to_png(svg, out_dir / "hello_card.png", dpi=300),
    }


if __name__ == "__main__":
    for kind, path in run().items():
        print(f"{kind}: {path}")
