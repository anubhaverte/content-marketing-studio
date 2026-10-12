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
    widths = _glyph_widths(font_path)
    current_size = font_size
    if _measure(text, widths) * current_size <= max_width:
        return TextFit((text,), current_size, False)

    low, high = min_font_size, font_size
    for _ in range(32):
        middle = (low + high) / 2
        if _measure(text, widths) * middle <= max_width:
            low = middle
        else:
            high = middle
    current_size = low if _measure(text, widths) * low <= max_width else min_font_size
    if _measure(text, widths) * current_size <= max_width:
        return TextFit((text,), current_size, False)

    lines, remaining = _wrap(text, widths, max_width / current_size, max_lines)
    if not remaining:
        return TextFit(tuple(lines), current_size, False)

    last = lines[-1] if lines else ""
    words = remaining.split()
    suffix = " ".join(words)
    shortened = True
    candidate = f"{last} {suffix}".strip()
    while candidate and _measure(candidate + "…", widths) * current_size > max_width:
        if " " in candidate:
            candidate = candidate.rsplit(" ", 1)[0]
        else:
            candidate = candidate[:-1]
    lines = lines[:max_lines]
    lines[-1] = f"{candidate}…" if candidate else "…"
    if _measure(lines[-1], widths) * current_size > max_width:
        raise ValueError("The ellipsis does not fit the configured text box at min_font_size")
    return TextFit(tuple(lines), current_size, shortened)


def measure_text(text: str, font_path: Path, font_size: float) -> float:
    """Measure text width in millimetres using the selected font's glyph metrics."""
    return _measure(text, _glyph_widths(font_path)) * font_size


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


def _measure(text: str, widths: dict[str, float]) -> float:
    """Sum actual advance widths, using the font's .notdef advance if needed."""
    missing = widths.get("\0", 0.6)
    return sum(widths.get(character, missing) for character in text)


def _wrap(text: str, widths: dict[str, float], width_limit: float, max_lines: int) -> tuple[list[str], str]:
    """Wrap at word boundaries and split only words too wide for one line."""
    lines: list[str] = []
    remaining = text.split()
    while remaining and len(lines) < max_lines:
        line = ""
        while remaining:
            proposed = f"{line} {remaining[0]}".strip()
            if _measure(proposed, widths) <= width_limit:
                line = proposed
                remaining.pop(0)
                continue
            if not line:
                word = remaining.pop(0)
                prefix = ""
                while word and _measure(prefix + word[0], widths) <= width_limit:
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
