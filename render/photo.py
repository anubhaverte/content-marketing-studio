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


def resolve_photo_path(
    path: str | Path,
    allowed_roots: list[Path] | Path | None = None,
) -> Path:
    """Safely resolve a photo path and guarantee it does not escape allowed directories.

    Raises:
        ValueError: If path traversal (e.g. '../') is attempted or if the path is outside allowed roots.
        FileNotFoundError: If the resolved path does not point to an existing file.
    """
    raw_str = str(path).replace("\\", "/")
    # Reject directory traversal attempts immediately
    if ".." in raw_str.split("/"):
        raise ValueError(f"Path traversal detected: {path!r}")

    p = Path(path)

    # Determine allowed roots
    repo_root = Path(__file__).resolve().parent.parent
    default_roots = [
        (repo_root / "sample_data" / "photos").resolve(),
        (repo_root / "assets").resolve(),
    ]
    if allowed_roots is None:
        roots = default_roots
    elif isinstance(allowed_roots, Path):
        roots = [allowed_roots.resolve()]
    else:
        roots = [r.resolve() for r in allowed_roots]

    if p.is_absolute():
        resolved = p.resolve()
        is_safe = any(
            resolved == r or r in resolved.parents
            for r in roots
        )
        if not is_safe:
            raise ValueError(f"Absolute photo path is outside allowed directories: {path!r}")
    else:
        # Relative path: resolve against each root in order
        found: Path | None = None
        for r in roots:
            candidate = (r / p).resolve()
            if candidate == r or r in candidate.parents:
                if candidate.is_file():
                    found = candidate
                    break
        if found is not None:
            resolved = found
        else:
            candidate = (roots[0] / p).resolve()
            if candidate != roots[0] and roots[0] not in candidate.parents:
                raise ValueError(f"Photo path must remain inside allowed directory: {path!r}")
            resolved = candidate

    if not resolved.is_file():
        raise FileNotFoundError(f"Photo file not found: {resolved}")

    return resolved


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
    allowed_roots: list[Path] | Path | None = None,
) -> tuple[str, tuple[int, int]]:
    """Embed readable photo bytes, face-cropped to frame aspect ratio using OpenCV."""
    import io
    import sys
    import warnings

    # Security check: validate traversal
    raw_str = str(path).replace("\\", "/")
    if ".." in raw_str.split("/"):
        raise ValueError(f"Path traversal detected in photo path: {path!r}")

    if allowed_roots is not None:
        path = resolve_photo_path(path, allowed_roots=allowed_roots)

    try:
        from app.assets import photo_utils
    except ImportError:
        backend_dir = Path(__file__).resolve().parent.parent / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from app.assets import photo_utils

    # Verify basic readability and get original dimensions
    with Image.open(path) as image:
        orig_width, orig_height = image.size
        image_format = image.format
        image.verify()
    if orig_width <= 0 or orig_height <= 0:
        raise ValueError(f"Photo dimensions must be positive: {path}")

    # 1. Run resolution check (300 DPI target for print)
    if not photo_utils.check_resolution(path, width, height, dpi=300):
        req_w = round(width * 300 / 25.4)
        req_h = round(height * 300 / 25.4)
        warnings.warn(
            f"Photo '{path.name}' has insufficient resolution ({orig_width}x{orig_height} px) "
            f"for {width:.1f}x{height:.1f} mm at 300 DPI (expected >= {req_w}x{req_h} px)"
        )

    # 2. Run blur check
    try:
        score = photo_utils.blur_score(path)
        if score < 100.0:
            warnings.warn(f"Photo '{path.name}' may be blurry (blur score {score:.1f} < 100)")
    except Exception as blur_err:
        warnings.warn(f"Could not compute blur score for '{path.name}': {blur_err}")

    # 3. Perform OpenCV face-aware crop
    try:
        cropped_bytes = photo_utils.face_crop(path, width, height)
        with Image.open(io.BytesIO(cropped_bytes)) as cropped_img:
            image_width, image_height = cropped_img.size
            crop_format = cropped_img.format or image_format
        encoded = base64.b64encode(cropped_bytes).decode("ascii")
        crop_mode = "face-aware"
    except Exception as crop_err:
        warnings.warn(f"Face crop failed for '{path.name}': {crop_err}; falling back to raw photo")
        image_width, image_height = orig_width, orig_height
        crop_format = image_format
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        crop_mode = "fallback-center"

    scale = max(width / image_width, height / image_height)
    rendered_width = image_width * scale
    rendered_height = image_height * scale
    image_x = x + (width - rendered_width) / 2
    image_y = y + (height - rendered_height) / 2
    clip_id = f"{element_id}-clip"
    media_type = Image.MIME.get(crop_format or "")
    if media_type is None:
        raise ValueError(f"Unsupported photo format: {crop_format or path.suffix}")
    clip_shape = (
        f'<circle cx="{x + width / 2:g}" cy="{y + height / 2:g}" r="{min(width, height) / 2:g}"/>'
        if shape == "circle"
        else f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{radius:g}"/>'
    )
    return (
        f'<defs><clipPath id="{clip_id}">{clip_shape}</clipPath></defs>'
        f'<image id="{escape(element_id)}" data-photo-status="embedded" data-crop-mode="{crop_mode}" '
        f'data-source-size="{image_width} {image_height}" x="{image_x:g}" y="{image_y:g}" '
        f'width="{rendered_width:g}" height="{rendered_height:g}" preserveAspectRatio="xMidYMid meet" '
        f'clip-path="url(#{clip_id})" href="data:{media_type};base64,{encoded}"/>',
        (orig_width, orig_height),
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
