"""Fit text using the real bundled font metrics."""

from pathlib import Path
import sys
from typing import Any

from app.spec.constants import MM_PER_PT
from app.config import ROOT

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from render.text_fit import (  # noqa: E402
    find_font_file,
    fit_text as _fit_text,
    measure_text_vertical_bounds,
)


def resolve_font(family: str, bold: bool) -> tuple[str, Path]:
    """Find the exact repository or system font requested by the theme."""
    return find_font_file([family], "700" if bold else "400")


def fit_text(
    text: str,
    font_path: Path,
    box_w_mm: float,
    max_pt: float,
    min_pt: float,
    max_lines: int,
) -> dict[str, Any]:
    """Fit text into its width, retaining an explicit shortening flag."""
    result = _fit_text(
        text,
        font_path=font_path,
        font_size=max_pt * MM_PER_PT,
        min_font_size=min_pt * MM_PER_PT,
        max_width=box_w_mm,
        max_lines=max_lines,
    )
    return {
        "lines": result.lines,
        "font_size": result.font_size,
        "shortened": result.shortened,
    }
