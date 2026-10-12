"""Create aspect-preserving, clipped photo markup with initials fallbacks."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape

from PIL import Image


PhotoShape = Literal["circle", "rounded_rect"]


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
        f'<text x="{x + width / 2:g}" y="{y + height / 2:g}" text-anchor="middle" '
        f'dominant-baseline="middle" font-size="{min(width, height) * 0.28:g}" '
        f'font-weight="700" fill="#FFFFFF">{escape(label)}</text></g>'
    )
