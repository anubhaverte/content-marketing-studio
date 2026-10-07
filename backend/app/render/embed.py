"""Helpers to embed files inside an SVG as data URIs.

All images in our SVG files are embedded (never linked by file path), so one
SVG file is fully self-contained and prints the same on any computer.
"""
import base64
from pathlib import Path

MIME_TYPES = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def file_to_data_uri(path: Path) -> str:
    """Read an image file and return it as a base64 data URI string."""
    path = Path(path)
    mime = MIME_TYPES.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"Unsupported image type '{path.suffix}' for {path.name}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
