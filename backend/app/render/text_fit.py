"""Fit text into a box using the real font width.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional


def fit_text(text: str, font_path: Path, box_w_mm: float, max_pt: float, min_pt: float, max_lines: int) -> dict[str, Any]:
    """Shrink from max to min font size; then wrap; then shorten safely (e.g. abbreviate a middle name) and flag it. Return the lines, the font size and a 'shortened' flag.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Shrink from max to min font size; then wrap; then shorten safely (e")
