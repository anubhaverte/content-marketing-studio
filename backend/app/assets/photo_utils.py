"""Photo helpers: face-centered crop and quality checks.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional


def face_crop(photo_path: Path, out_w_mm: float, out_h_mm: float) -> bytes:
    """Crop around the detected face to the frame's aspect ratio. Never squash. Fall back to a centered crop.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: Crop around the detected face to the frame's aspect ratio")


def blur_score(photo_path: Path) -> float:
    """Return the variance of the Laplacian (low = blurry).

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: Return the variance of the Laplacian (low = blurry)")


def check_resolution(photo_path: Path, w_mm: float, h_mm: float, dpi: int = 300) -> bool:
    """True if the photo has enough pixels for the printed size at the given DPI.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: True if the photo has enough pixels for the printed size at the given DPI")
