"""Create aspect-preserving, clipped photo markup with initials fallbacks."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape

from PIL import Image


PhotoShape = Literal["circle", "rounded_rect"]


def best_contrast_text_color(background: str, colors: dict[str, str]) -> tuple[str, str]:
    """Select the higher-contrast theme text color for an initials fallback."""
    candidates = {
        name: colors.get(name)
        for name in ("text", "text_on_primary")
    }
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", background):
        raise ValueError(f"Initials background must be a six-digit theme color: {background!r}")
    if any(not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value) for value in candidates.values()):
        raise ValueError("Theme must define valid 'text' and 'text_on_primary' colors")
    name, color = max(
        candidates.items(),
        key=lambda item: _contrast_ratio(background, item[1]),
    )
    if _contrast_ratio(background, color) < 4.5:
        raise ValueError(
            f"Neither theme text color has 4.5:1 contrast with initials background {background}"
        )
    return name, color


def photo_markup(
    path: Path,
    *,
    element_id: str,
    x: float,
    y: float,
    width: float,
    height: float,
    shape: PhotoShape,
    radius: float,
) -> tuple[str, tuple[int, int]]:
    """Embed readable photo bytes, center-cropped without distorting their aspect ratio."""
    with Image.open(path) as image:
        image_width, image_height = image.size
        image_format = image.format
        image.verify()
    if image_width <= 0 or image_height <= 0:
        raise ValueError(f"Photo dimensions must be positive: {path}")

    scale = max(width / image_width, height / image_height)
    rendered_width = image_width * scale
    rendered_height = image_height * scale
    image_x = x + (width - rendered_width) / 2
    image_y = y + (height - rendered_height) / 2
    clip_id = f"{element_id}-clip"
    media_type = Image.MIME.get(image_format or "")
    if media_type is None:
        raise ValueError(f"Unsupported photo format: {image_format or path.suffix}")
    clip_shape = (
        f'<circle cx="{x + width / 2:g}" cy="{y + height / 2:g}" r="{min(width, height) / 2:g}"/>'
        if shape == "circle"
        else f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{radius:g}"/>'
    )
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f'<defs><clipPath id="{clip_id}">{clip_shape}</clipPath></defs>'
        f'<image id="{escape(element_id)}" data-photo-status="embedded" '
        f'data-source-size="{image_width} {image_height}" x="{image_x:g}" y="{image_y:g}" '
        f'width="{rendered_width:g}" height="{rendered_height:g}" preserveAspectRatio="xMidYMid meet" '
        f'clip-path="url(#{clip_id})" href="data:{media_type};base64,{encoded}"/>',
        (image_width, image_height),
    )


def initials(name: str | None) -> str:
    """Derive initials from the provided name without fabricating identity data."""
    if not name or not name.strip():
        return "?"
    parts = name.split()
    return "".join(part[0] for part in (parts if len(parts) == 1 else (parts[0], parts[-1]))).upper()


def initials_markup(
    *,
    element_id: str,
    label: str,
    x: float,
    y: float,
    width: float,
    height: float,
    shape: PhotoShape,
    radius: float,
    color: str,
    text_color: str,
    text_color_name: str,
) -> str:
    """Draw initials in a photo-shaped fallback area."""
    outline = (
        f'<circle cx="{x + width / 2:g}" cy="{y + height / 2:g}" r="{min(width, height) / 2:g}"/>'
        if shape == "circle"
        else f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{radius:g}"/>'
    )
    return (
        f'<g id="{escape(element_id)}" data-photo-status="fallback">'
        f'<defs><clipPath id="{escape(element_id)}-fallback-clip">{outline}</clipPath></defs>'
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" fill="{color}" '
        f'clip-path="url(#{escape(element_id)}-fallback-clip)"/>'
        f'<text id="{escape(element_id)}-initials" data-theme-color="{escape(text_color_name)}" '
        f'x="{x + width / 2:g}" y="{y + height / 2:g}" text-anchor="middle" '
        f'dominant-baseline="middle" font-size="{min(width, height) * 0.28:g}" '
        f'font-weight="700" fill="{escape(text_color)}">{escape(label)}</text></g>'
    )


def _contrast_ratio(first: str, second: str) -> float:
    """Return WCAG contrast for two six-digit RGB colors."""
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)
