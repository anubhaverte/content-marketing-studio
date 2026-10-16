"""SVG -> PDF export (vector, exact physical size)."""
from pathlib import Path

import cairosvg


def svg_to_pdf(svg_text: str, out_path: Path) -> Path:
    """Convert SVG text to a vector PDF. The page size comes from the SVG's width/height in mm."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2pdf(bytestring=svg_text.encode("utf-8"), write_to=str(out_path))
    return out_path
