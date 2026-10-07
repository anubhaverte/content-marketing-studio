"""SVG -> PNG export at a chosen DPI."""
from pathlib import Path

import cairosvg

from app.spec.constants import DEFAULT_DPI


def svg_to_png(svg_text: str, out_path: Path, dpi: int = DEFAULT_DPI) -> Path:
    """Convert SVG text to a PNG. Pixel size = size in mm / 25.4 * dpi."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), write_to=str(out_path), dpi=dpi)
    return out_path
