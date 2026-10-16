"""Build editable vector QR codes with a quiet zone."""

from __future__ import annotations

from xml.sax.saxutils import escape

import segno


def qr_svg_path(
    url: str,
    size_mm: float,
    *,
    x: float = 0,
    y: float = 0,
    color: str = "#000000",
    background: str = "#FFFFFF",
    element_id: str = "qr",
) -> str:
    """Return one path-based QR code including its four-module quiet zone."""
    if not url:
        raise ValueError("QR payload cannot be empty")
    if size_mm < 12:
        raise ValueError("QR code size must be at least 12 mm")

    code = segno.make(url, error="m", micro=False)
    matrix = code.matrix
    quiet_zone = 4
    modules = len(matrix) + quiet_zone * 2
    module_size = size_mm / modules
    path_data = "".join(
        f"M{column + quiet_zone} {row + quiet_zone}h1v1h-1z"
        for row, values in enumerate(matrix)
        for column, dark in enumerate(values)
        if dark
    )
    escaped_id = escape(element_id, {'"': "&quot;", "'": "&apos;"})
    escaped_url = escape(url, {'"': "&quot;", "'": "&apos;"})
    return (
        f'<g id="{escaped_id}" data-qr-payload="{escaped_url}" '
        f'data-qr-width-mm="{size_mm:g}" transform="translate({x:g} {y:g}) '
        f'scale({module_size:g})">'
        f'<path d="M0 0h{modules}v{modules}H0z" fill="{background}"/>'
        f'<path d="{path_data}" fill="{color}"/></g>'
    )
