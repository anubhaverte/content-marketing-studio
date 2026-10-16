"""Render vector QR codes from attendance URLs."""

from __future__ import annotations

import segno


def qr_markup(
    payload: str,
    *,
    element_id: str,
    x: float,
    y: float,
    size: float,
    color: str,
    background: str,
) -> str:
    """Generate a compact vector QR as one SVG path in the requested square."""
    if size < 12:
        raise ValueError("QR code size must be at least 12 mm")
    code = segno.make(payload, error="m", micro=False)
    matrix = code.matrix
    rows = len(matrix)
    columns = len(matrix[0])
    quiet_zone = 4
    total_width = columns + quiet_zone * 2
    total_height = rows + quiet_zone * 2
    module_size = size / max(total_width, total_height)
    path_data = "".join(
        f"M{column + quiet_zone} {row + quiet_zone}h1v1h-1z"
        for row, values in enumerate(matrix)
        for column, dark in enumerate(values)
        if dark
    )
    return (
        f'<g id="{element_id}" data-qr-width-mm="{size:g}" data-qr-payload="{_escape(payload)}" '
        f'transform="translate({x:g} {y:g}) scale({module_size:g})">'
        f'<path d="M0 0h{total_width}v{total_height}H0z" fill="{background}"/>'
        f'<path d="{path_data}" fill="{color}"/></g>'
    )


def _escape(value: str) -> str:
    """Escape QR payload metadata used in an XML attribute."""
    from xml.sax.saxutils import escape

    return escape(value, {'"': "&quot;", "'": "&apos;"})
