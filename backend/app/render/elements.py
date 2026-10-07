"""One drawing function per layout element type. Each returns an SVG snippet.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional


def draw_rect(el: Any, theme: Any) -> str:
    """Draw a rectangle or band.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw a rectangle or band")


def draw_line(el: Any, theme: Any) -> str:
    """Draw a (dashed) line.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw a (dashed) line")


def draw_circle(el: Any, theme: Any) -> str:
    """Draw a circle.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw a circle")


def draw_text(el: Any, theme: Any, text: str) -> str:
    """Draw auto-fitted text.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw auto-fitted text")


def draw_photo(el: Any, photo_uri: Optional[str], initials: str) -> str:
    """Draw the clipped photo, or an initials placeholder if there is none.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw the clipped photo, or an initials placeholder if there is none")


def draw_logo(el: Any, logo_uri: str) -> str:
    """Draw a logo with 'contain' fit.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw a logo with 'contain' fit")


def draw_role_badge(el: Any, theme: Any, role: str) -> str:
    """Draw the role strip using the theme's role color.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw the role strip using the theme's role color")


def draw_qr(el: Any, url: str) -> str:
    """Draw a vector QR code.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: Draw a vector QR code")


def draw_svg_asset(el: Any) -> str:
    """Draw an SVG artwork file from assets/art.

    Implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: Draw an SVG artwork file from assets/art")
