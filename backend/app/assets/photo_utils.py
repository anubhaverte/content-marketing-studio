"""Photo helpers: face-centered crop, blur detection, and resolution checks using OpenCV.

Owned by Person 2 per docs/OWNERS.json.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


def detect_faces(img: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Detect faces in a BGR image using OpenCV.

    Returns a list of bounding boxes (x, y, w, h), sorted by area (largest first).
    Uses OpenCV YCrCb + HSV skin-color segmentation with morphological filtering
    and aspect-ratio verification.
    """
    if img is None or img.size == 0:
        return []

    orig_h, orig_w = img.shape[:2]
    if orig_h < 10 or orig_w < 10:
        return []

    # 1. Convert to YCrCb and HSV color spaces for robust skin-tone extraction
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask_hsv = cv2.inRange(hsv, np.array([0, 15, 35], dtype=np.uint8), np.array([35, 255, 255], dtype=np.uint8))

    combined_mask = cv2.bitwise_and(mask_ycrcb, mask_hsv)

    # 2. Morphological cleanup to join facial regions and eliminate noise
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel_open, iterations=1)

    # 3. Find candidate contours
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    faces: list[tuple[int, int, int, int]] = []
    min_area = orig_h * orig_w * 0.012  # Face should be at least ~1.2% of total image

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        aspect = h / float(w)
        # Human faces/heads typically have height-to-width ratios between 0.6 and 2.5
        if 0.55 <= aspect <= 2.8:
            faces.append((x, y, w, h))

    # Sort faces by area descending (primary/prominent face first)
    faces.sort(key=lambda b: b[2] * b[3], reverse=True)
    return faces


def face_crop(photo_path: Path | str, out_w_mm: float, out_h_mm: float) -> bytes:
    """Crop around the detected face to the frame's aspect ratio. Never squash.

    Falls back to a centered crop if no face is detected.
    Returns encoded image bytes (PNG if source is .png, else JPEG).
    """
    path = Path(photo_path)
    if not path.is_file():
        raise FileNotFoundError(f"Photo file not found: {path}")

    if out_w_mm <= 0 or out_h_mm <= 0:
        raise ValueError(f"Output frame dimensions must be positive: {out_w_mm} x {out_h_mm}")

    # Read image with OpenCV
    img = cv2.imread(str(path))
    if img is None or img.size == 0:
        raise ValueError(f"Corrupt or unreadable image: {path}")

    orig_h, orig_w = img.shape[:2]
    target_aspect = float(out_w_mm) / float(out_h_mm)

    # Detect faces
    faces = detect_faces(img)

    if faces:
        # Focus on the primary face
        fx, fy, fw, fh = faces[0]
        cx = fx + fw / 2.0
        # Position vertical center slightly above face midpoint to include hair/forehead
        cy = fy + fh * 0.45

        # Face should ideally occupy ~50-60% of crop height for portrait card badges
        scale = 1.85
        crop_h = fh * scale
        crop_w = crop_h * target_aspect

        # Clamp if crop dimensions exceed image boundaries
        if crop_w > orig_w or crop_h > orig_h:
            if orig_w / float(orig_h) > target_aspect:
                crop_h = float(orig_h)
                crop_w = float(orig_h) * target_aspect
            else:
                crop_w = float(orig_w)
                crop_h = float(orig_w) / target_aspect

        crop_w_int = max(1, int(round(crop_w)))
        crop_h_int = max(1, int(round(crop_h)))

        x1 = int(round(cx - crop_w_int / 2.0))
        y1 = int(round(cy - crop_h_int / 2.0))

        # Clamp offsets to stay within image bounds
        x1 = max(0, min(orig_w - crop_w_int, x1))
        y1 = max(0, min(orig_h - crop_h_int, y1))
    else:
        # Fall back to a centered crop matching target aspect ratio
        if orig_w / float(orig_h) > target_aspect:
            crop_h_int = orig_h
            crop_w_int = max(1, int(round(orig_h * target_aspect)))
            x1 = (orig_w - crop_w_int) // 2
            y1 = 0
        else:
            crop_w_int = orig_w
            crop_h_int = max(1, int(round(orig_w / target_aspect)))
            x1 = 0
            y1 = (orig_h - crop_h_int) // 2

    # Perform slice crop
    cropped = img[y1:y1 + crop_h_int, x1:x1 + crop_w_int]
    if cropped.size == 0:
        raise ValueError(f"Cropped image has zero pixels: {path}")

    # Encode result to bytes
    suffix = path.suffix.lower()
    if suffix == ".png":
        success, encoded = cv2.imencode(".png", cropped)
    else:
        success, encoded = cv2.imencode(".jpg", cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

    if not success:
        raise ValueError(f"Failed to encode cropped image for {path}")

    return encoded.tobytes()


def blur_score(photo_path: Path | str) -> float:
    """Return the variance of the Laplacian (low = blurry).

    Scores typically < 100.0 indicate noticeability blurry or out-of-focus photos.
    """
    path = Path(photo_path)
    if not path.is_file():
        raise FileNotFoundError(f"Photo file not found: {path}")

    gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if gray is None or gray.size == 0:
        raise ValueError(f"Corrupt or unreadable image: {path}")

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def check_resolution(photo_path: Path | str, w_mm: float, h_mm: float, dpi: int = 300) -> bool:
    """True if the photo has enough pixels for the printed size at the given DPI."""
    path = Path(photo_path)
    if not path.is_file():
        raise FileNotFoundError(f"Photo file not found: {path}")

    if w_mm <= 0 or h_mm <= 0 or dpi <= 0:
        return False

    req_w = round(w_mm * dpi / 25.4)
    req_h = round(h_mm * dpi / 25.4)

    try:
        with Image.open(path) as img:
            width, height = img.size
    except Exception as error:
        raise ValueError(f"Corrupt or unreadable image: {path} ({error})") from error

    return width >= req_w and height >= req_h


def check_photo_quality(
    photo_path: Path | str,
    w_mm: float,
    h_mm: float,
    dpi: int = 300,
    blur_threshold: float = 100.0,
) -> dict[str, Any]:
    """Inspect photo resolution, blur score, and face presence, returning actionable warnings."""
    path = Path(photo_path)
    if not path.is_file():
        return {
            "valid": False,
            "warnings": [f"Photo not found: {path}"],
            "blur_score": 0.0,
            "is_blurry": True,
            "has_sufficient_resolution": False,
            "face_count": 0,
        }

    issues: list[str] = []

    # 1. Resolution check
    res_ok = check_resolution(path, w_mm, h_mm, dpi=dpi)
    if not res_ok:
        try:
            with Image.open(path) as img:
                w_px, h_px = img.size
        except Exception:
            w_px, h_px = 0, 0
        req_w = round(w_mm * dpi / 25.4)
        req_h = round(h_mm * dpi / 25.4)
        issues.append(
            f"Photo '{path.name}' has insufficient resolution ({w_px}x{h_px} px) "
            f"for {w_mm}x{h_mm} mm at {dpi} DPI (requires >= {req_w}x{req_h} px)"
        )

    # 2. Blur check
    try:
        b_score = blur_score(path)
        is_blurry = b_score < blur_threshold
        if is_blurry:
            issues.append(
                f"Photo '{path.name}' may be blurry (blur score {b_score:.1f} < threshold {blur_threshold})"
            )
    except Exception as error:
        b_score = 0.0
        is_blurry = True
        issues.append(f"Could not compute blur score for '{path.name}': {error}")

    # 3. Face detection
    try:
        img = cv2.imread(str(path))
        faces = detect_faces(img)
        face_count = len(faces)
        if face_count == 0:
            issues.append(f"No face detected in photo '{path.name}'; falling back to center crop")
    except Exception as error:
        face_count = 0
        issues.append(f"Face detection failed for '{path.name}': {error}")

    return {
        "valid": True,
        "warnings": issues,
        "blur_score": b_score,
        "is_blurry": is_blurry,
        "has_sufficient_resolution": res_ok,
        "face_count": face_count,
    }
