"""Measure and fit SVG text using the actual font file selected for rendering."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fontTools.ttLib import TTFont


@dataclass(frozen=True)
class TextFit:
    """Fitted text lines, font size in millimetres, and truncation status."""

    lines: tuple[str, ...]
    font_size: float
    shortened: bool


def find_font_file(families: Iterable[str], weight: str = "400") -> tuple[str, Path]:
    """Return the first installed font file matching the configured families."""
    windows = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    local_fonts = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
    bold = _is_bold(weight)
    known = {
        "arial": (("arialbd.ttf" if bold else "arial.ttf"),),
        "segoe ui": (("seguisb.ttf" if bold else "segoeui.ttf"),),
        "dejavu sans": (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),),
    }
    for family in families:
        candidates = known.get(family.casefold(), ())
        paths = [windows / name for name in candidates]
        paths.extend(local_fonts / name for name in candidates)
        if family.casefold() == "dejavu sans":
            paths.append(Path("/usr/share/fonts/truetype/dejavu") / candidates[0])
        for path in paths:
            if path.is_file():
                return family, path
    raise FileNotFoundError(
        f"No installed font file was found for configured font families: {', '.join(families)}"
    )


def fit_text(
    text: str,
    *,
    font_path: Path,
    font_size: float,
    min_font_size: float,
    max_width: float,
    max_lines: int,
) -> TextFit:
    """Shrink, then wrap, and truncate with an ellipsis only if still necessary."""
    if min_font_size > font_size:
        raise ValueError("min_font_size cannot exceed font_size")
    if max_width <= 0 or max_lines <= 0:
        raise ValueError("Text max_width and max_lines must be greater than zero")
    usable_width = max_width - 0.01
    if usable_width <= 0:
        raise ValueError("Text max_width must be greater than 0.01 mm")
    widths = _glyph_widths(font_path)
    glyph_bounds = _glyph_ink_bounds(font_path)
    current_size = font_size
    if _centered_ink_width(text, widths, glyph_bounds) * current_size <= usable_width:
        return TextFit((text,), current_size, False)

    low, high = min_font_size, font_size
    for _ in range(32):
        middle = (low + high) / 2
        if _centered_ink_width(text, widths, glyph_bounds) * middle <= usable_width:
            low = middle
        else:
            high = middle
    current_size = (
        low
        if _centered_ink_width(text, widths, glyph_bounds) * low <= usable_width
        else min_font_size
    )
    if _centered_ink_width(text, widths, glyph_bounds) * current_size <= usable_width:
        return TextFit((text,), current_size, False)

    lines, remaining = _wrap(
        text, widths, glyph_bounds, usable_width / current_size, max_lines
    )
    if not remaining:
        return TextFit(tuple(lines), current_size, False)

    last = lines[-1] if lines else ""
    words = remaining.split()
    suffix = " ".join(words)
    shortened = True
    candidate = f"{last} {suffix}".strip()
    while candidate and _centered_ink_width(
        candidate + "…", widths, glyph_bounds
    ) * current_size > usable_width:
        if " " in candidate:
            candidate = candidate.rsplit(" ", 1)[0]
        else:
            candidate = candidate[:-1]
    lines = lines[:max_lines]
    lines[-1] = f"{candidate}…" if candidate else "…"
    if _centered_ink_width(lines[-1], widths, glyph_bounds) * current_size > usable_width:
        raise ValueError("The ellipsis does not fit the configured text box at min_font_size")
    return TextFit(tuple(lines), current_size, shortened)


def measure_text(text: str, font_path: Path, font_size: float) -> float:
    """Measure the ink width in millimetres, including glyph side bearings."""
    left, right, _, _, _ = measure_text_bounds(text, font_path, font_size)
    return right - left


def measure_text_bounds(
    text: str,
    font_path: Path,
    font_size: float,
) -> tuple[float, float, float, float, float]:
    """Return ink bounds and advance in mm relative to the text baseline."""
    font = TTFont(font_path, lazy=True)
    try:
        units_per_em = font["head"].unitsPerEm
        cmap = font.getBestCmap()
        glyphs = font["glyf"]
        metrics = font["hmtx"].metrics
        pen_x = 0
        left: int | None = None
        right: int | None = None
        top = 0
        bottom = 0
        for character in text:
            glyph_name = cmap.get(ord(character), ".notdef")
            glyph = glyphs[glyph_name]
            if hasattr(glyph, "xMin") and hasattr(glyph, "xMax"):
                glyph_left = pen_x + glyph.xMin
                glyph_right = pen_x + glyph.xMax
                left = glyph_left if left is None else min(left, glyph_left)
                right = glyph_right if right is None else max(right, glyph_right)
                top = max(top, glyph.yMax)
                bottom = min(bottom, glyph.yMin)
            pen_x += metrics[glyph_name][0]
        if left is None or right is None:
            left, right = 0, pen_x
        scale = font_size / units_per_em
        return left * scale, right * scale, top * scale, -bottom * scale, pen_x * scale
    except (KeyError, AttributeError, OSError, ValueError) as error:
        raise ValueError(f"Could not read glyph bounds from {font_path}: {error}") from error
    finally:
        font.close()


def measure_text_vertical_bounds(text: str, font_path: Path, font_size: float) -> tuple[float, float]:
    """Return the rendered glyph ascent and descent in millimetres."""
    _, _, ascent, descent, _ = measure_text_bounds(text, font_path, font_size)
    return ascent, descent


def _glyph_widths(font_path: Path) -> dict[str, float]:
    """Load normalized glyph widths from the font's cmap and horizontal metrics."""
    try:
        font = TTFont(font_path, lazy=True)
        try:
            units_per_em = font["head"].unitsPerEm
            cmap = font.getBestCmap()
            metrics = font["hmtx"].metrics
            widths = {
                character: metrics[glyph_name][0] / units_per_em
                for codepoint, glyph_name in cmap.items()
                for character in (chr(codepoint),)
            }
            widths["\0"] = metrics.get(".notdef", (units_per_em * 0.6, 0))[0] / units_per_em
            return widths
        finally:
            font.close()
    except (OSError, KeyError, ValueError) as error:
        raise ValueError(f"Could not read font metrics from {font_path}: {error}") from error


def _glyph_ink_bounds(font_path: Path) -> dict[str, tuple[float, float]]:
    """Load each glyph's horizontal ink bounds, including its side bearings."""
    try:
        font = TTFont(font_path, lazy=True)
        try:
            units_per_em = font["head"].unitsPerEm
            cmap = font.getBestCmap()
            glyphs = font["glyf"]
            bounds = {}
            for codepoint, glyph_name in cmap.items():
                glyph = glyphs[glyph_name]
                if hasattr(glyph, "xMin") and hasattr(glyph, "xMax"):
                    bounds[chr(codepoint)] = (
                        glyph.xMin / units_per_em,
                        glyph.xMax / units_per_em,
                    )
            notdef = glyphs[".notdef"]
            if hasattr(notdef, "xMin") and hasattr(notdef, "xMax"):
                bounds["\0"] = (notdef.xMin / units_per_em, notdef.xMax / units_per_em)
            return bounds
        finally:
            font.close()
    except (OSError, KeyError, ValueError) as error:
        raise ValueError(f"Could not read glyph bounds from {font_path}: {error}") from error


def _centered_ink_width(
    text: str,
    advances: dict[str, float],
    glyph_bounds: dict[str, tuple[float, float]],
) -> float:
    """Return the full ink width around the SVG text-anchor middle position."""
    advance = 0.0
    left: float | None = None
    right: float | None = None
    missing = glyph_bounds.get("\0", (0.0, 0.0))
    for character in text:
        glyph_left, glyph_right = glyph_bounds.get(character, missing)
        left = advance + glyph_left if left is None else min(left, advance + glyph_left)
        right = advance + glyph_right if right is None else max(right, advance + glyph_right)
        advance += advances.get(character, advances.get("\0", 0.6))
    if left is None or right is None:
        left, right = 0.0, advance
    return 2 * max(abs(left - advance / 2), abs(right - advance / 2))


def _measure(text: str, widths: dict[str, float]) -> float:
    """Sum actual advance widths, using the font's .notdef advance if needed."""
    missing = widths.get("\0", 0.6)
    return sum(widths.get(character, missing) for character in text)


def _wrap(
    text: str,
    widths: dict[str, float],
    glyph_bounds: dict[str, tuple[float, float]],
    width_limit: float,
    max_lines: int,
) -> tuple[list[str], str]:
    """Wrap at word boundaries and split only words too wide for one line."""
    lines: list[str] = []
    remaining = text.split()
    while remaining and len(lines) < max_lines:
        line = ""
        while remaining:
            proposed = f"{line} {remaining[0]}".strip()
            if _centered_ink_width(proposed, widths, glyph_bounds) <= width_limit:
                line = proposed
                remaining.pop(0)
                continue
            if not line:
                word = remaining.pop(0)
                prefix = ""
                while word and _centered_ink_width(
                    prefix + word[0], widths, glyph_bounds
                ) <= width_limit:
                    prefix += word[0]
                    word = word[1:]
                if not prefix:
                    raise ValueError("A glyph is wider than the text box at min_font_size")
                line = prefix
                if word:
                    remaining.insert(0, word)
            break
        lines.append(line)
    return lines, " ".join(remaining)


def _is_bold(weight: str) -> bool:
    """Recognize common numeric and named bold font weights."""
    return bool(re.search(r"bold|semibold|[6-9]00", weight, re.IGNORECASE))
