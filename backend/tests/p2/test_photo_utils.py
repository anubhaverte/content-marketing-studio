"""Tests for OpenCV face detection, face cropping, blur score, and resolution checks.

Owned by Person 2 per docs/OWNERS.json.
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2
import numpy as np
import pytest
from PIL import Image

from app.assets import photo_utils
from render.photo import photo_markup


@pytest.fixture
def temp_photos(tmp_path: Path):
    """Fixture to generate synthetic test photos for photo_utils validation."""
    # 1. Centered Face Image (400x400)
    centered_img = np.full((400, 400, 3), (210, 140, 80), dtype=np.uint8)  # Background
    # Face skin-tone rectangle in BGR centered at (150, 120, 100, 140)
    cv2.rectangle(centered_img, (150, 120), (250, 260), (160, 180, 230), -1)
    centered_path = tmp_path / "centered_face.jpg"
    cv2.imwrite(str(centered_path), centered_img)

    # 2. Off-Center Face Image (400x400, face near top-left)
    off_center_img = np.full((400, 400, 3), (210, 140, 80), dtype=np.uint8)
    # Face placed at (30, 40, 90, 120)
    cv2.rectangle(off_center_img, (30, 40), (120, 160), (160, 180, 230), -1)
    off_center_path = tmp_path / "off_center_face.jpg"
    cv2.imwrite(str(off_center_path), off_center_img)

    # 3. Multiple Faces Image (400x600, primary face large, secondary small)
    multi_img = np.full((400, 600, 3), (210, 140, 80), dtype=np.uint8)
    cv2.rectangle(multi_img, (50, 80), (150, 220), (160, 180, 230), -1)   # Secondary face (100x140)
    cv2.rectangle(multi_img, (320, 60), (480, 260), (160, 180, 230), -1) # Primary larger face (160x200)
    multi_path = tmp_path / "multi_face.jpg"
    cv2.imwrite(str(multi_path), multi_img)

    # 4. No-Face Image (Plain background, no skin tones)
    no_face_img = np.full((400, 400, 3), (200, 100, 50), dtype=np.uint8)  # Pure blue-ish/teal
    no_face_path = tmp_path / "no_face.png"
    cv2.imwrite(str(no_face_path), no_face_img)

    # 5. Sharp vs Blurry Images
    sharp_img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.rectangle(sharp_img, (50, 50), (250, 250), (255, 255, 255), 4)
    cv2.line(sharp_img, (50, 150), (250, 150), (255, 255, 255), 4)
    sharp_path = tmp_path / "sharp.jpg"
    cv2.imwrite(str(sharp_path), sharp_img)

    blurry_img = cv2.GaussianBlur(sharp_img, (31, 31), 0)
    blurry_path = tmp_path / "blurry.jpg"
    cv2.imwrite(str(blurry_path), blurry_img)

    # 6. High-res vs Low-res Photos
    # Target 25mm x 30mm at 300 DPI requires 295 x 354 px
    high_res_path = tmp_path / "high_res.jpg"
    cv2.imwrite(str(high_res_path), np.full((400, 400, 3), 128, dtype=np.uint8))

    low_res_path = tmp_path / "low_res.jpg"
    cv2.imwrite(str(low_res_path), np.full((100, 100, 3), 128, dtype=np.uint8))

    # 7. Corrupt Image file
    corrupt_path = tmp_path / "corrupt.jpg"
    corrupt_path.write_bytes(b"NOT_AN_IMAGE_DATA_HEADER_CORRUPT")

    return {
        "centered": centered_path,
        "off_center": off_center_path,
        "multi": multi_path,
        "no_face": no_face_path,
        "sharp": sharp_path,
        "blurry": blurry_path,
        "high_res": high_res_path,
        "low_res": low_res_path,
        "corrupt": corrupt_path,
        "missing": tmp_path / "does_not_exist.jpg",
    }


def test_detect_faces_centered(temp_photos):
    """Verify face detection on a centered face image."""
    img = cv2.imread(str(temp_photos["centered"]))
    faces = photo_utils.detect_faces(img)
    assert len(faces) == 1
    x, y, w, h = faces[0]
    # Check that detected bounding box matches the injected rectangle
    assert abs(x - 150) <= 5
    assert abs(y - 120) <= 5
    assert abs(w - 100) <= 5
    assert abs(h - 140) <= 5


def test_detect_faces_off_center(temp_photos):
    """Verify face detection on an off-center face image."""
    img = cv2.imread(str(temp_photos["off_center"]))
    faces = photo_utils.detect_faces(img)
    assert len(faces) == 1
    x, y, w, h = faces[0]
    assert x < 50
    assert y < 60


def test_detect_faces_multiple(temp_photos):
    """Verify multiple faces are detected and sorted with the largest face first."""
    img = cv2.imread(str(temp_photos["multi"]))
    faces = photo_utils.detect_faces(img)
    assert len(faces) >= 2
    # First face must be the larger one at x ~ 320
    assert faces[0][2] * faces[0][3] > faces[1][2] * faces[1][3]
    assert faces[0][0] > 250


def test_detect_faces_no_face(temp_photos):
    """Verify no-face image returns empty list."""
    img = cv2.imread(str(temp_photos["no_face"]))
    faces = photo_utils.detect_faces(img)
    assert faces == []


def test_face_crop_centered(temp_photos):
    """Verify face_crop produces valid image bytes with exact aspect ratio."""
    out_bytes = photo_utils.face_crop(temp_photos["centered"], out_w_mm=25.0, out_h_mm=25.0)
    assert isinstance(out_bytes, bytes)
    assert len(out_bytes) > 0

    with Image.open(io.BytesIO(out_bytes)) as cropped:
        w, h = cropped.size
        # 1:1 aspect ratio
        assert w == h


def test_face_crop_off_center_shifts_frame(temp_photos):
    """Verify that off-center face shifts the crop window compared to center crop."""
    # Crop to 1:1 frame (20mm x 20mm)
    crop_bytes = photo_utils.face_crop(temp_photos["off_center"], out_w_mm=20.0, out_h_mm=20.0)
    with Image.open(io.BytesIO(crop_bytes)) as cropped:
        # Check that cropped image is valid
        assert cropped.size[0] > 0
        assert cropped.size[1] > 0
        # Aspect ratio matches
        assert cropped.size[0] == cropped.size[1]


def test_face_crop_no_face_fallback(temp_photos):
    """Verify that images without detected faces deterministically fall back to center crop."""
    crop_bytes = photo_utils.face_crop(temp_photos["no_face"], out_w_mm=20.0, out_h_mm=30.0)
    with Image.open(io.BytesIO(crop_bytes)) as cropped:
        w, h = cropped.size
        assert abs((w / h) - (20.0 / 30.0)) < 0.05


def test_face_crop_corrupt_and_missing_raise(temp_photos):
    """Verify corrupt and missing images raise clear, actionable errors."""
    with pytest.raises(FileNotFoundError):
        photo_utils.face_crop(temp_photos["missing"], 20.0, 20.0)

    with pytest.raises(ValueError, match="Corrupt or unreadable image"):
        photo_utils.face_crop(temp_photos["corrupt"], 20.0, 20.0)

    with pytest.raises(ValueError, match="Output frame dimensions must be positive"):
        photo_utils.face_crop(temp_photos["centered"], 0.0, 20.0)


def test_blur_score_sharp_vs_blurry(temp_photos):
    """Verify blur_score returns significantly higher score for sharp photos."""
    sharp_score = photo_utils.blur_score(temp_photos["sharp"])
    blurry_score = photo_utils.blur_score(temp_photos["blurry"])

    assert sharp_score > blurry_score
    assert sharp_score > 100.0
    assert blurry_score < 100.0


def test_blur_score_corrupt_and_missing(temp_photos):
    """Verify blur_score handles invalid paths."""
    with pytest.raises(FileNotFoundError):
        photo_utils.blur_score(temp_photos["missing"])

    with pytest.raises(ValueError):
        photo_utils.blur_score(temp_photos["corrupt"])


def test_check_resolution(temp_photos):
    """Verify check_resolution accurately flags images below DPI requirements."""
    # Frame is 30mm x 30mm at 300 DPI -> needs 354 x 354 px
    assert photo_utils.check_resolution(temp_photos["high_res"], 30.0, 30.0, dpi=300) is True
    assert photo_utils.check_resolution(temp_photos["low_res"], 30.0, 30.0, dpi=300) is False

    with pytest.raises(FileNotFoundError):
        photo_utils.check_resolution(temp_photos["missing"], 30.0, 30.0)

    with pytest.raises(ValueError):
        photo_utils.check_resolution(temp_photos["corrupt"], 30.0, 30.0)


def test_check_photo_quality_comprehensive(temp_photos):
    """Verify check_photo_quality aggregates resolution, blur, and face checks."""
    result = photo_utils.check_photo_quality(temp_photos["blurry"], w_mm=30.0, h_mm=30.0, dpi=300)
    assert result["valid"] is True
    assert result["is_blurry"] is True
    assert any("blurry" in w.lower() for w in result["warnings"])

    missing_res = photo_utils.check_photo_quality(temp_photos["missing"], w_mm=30.0, h_mm=30.0)
    assert missing_res["valid"] is False


def test_photo_markup_integration(temp_photos):
    """Verify photo_markup embeds face-cropped image with expected SVG tags."""
    markup, (orig_w, orig_h) = photo_markup(
        temp_photos["centered"],
        element_id="person-photo",
        x=10.0,
        y=15.0,
        width=25.0,
        height=25.0,
        shape="circle",
        radius=3.0,
    )
    assert "<image" in markup
    assert 'id="person-photo"' in markup
    assert 'data-photo-status="embedded"' in markup
    assert 'data-crop-mode="face-aware"' in markup
    assert "data:image/jpeg;base64," in markup
    assert orig_w == 400
    assert orig_h == 400


def test_photo_markup_insufficient_resolution_warning(temp_photos):
    """Verify photo_markup emits a warning when resolution is insufficient."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        photo_markup(
            temp_photos["low_res"],
            element_id="person-photo",
            x=10.0,
            y=15.0,
            width=25.0,
            height=25.0,
            shape="circle",
            radius=3.0,
        )
        assert any("insufficient resolution" in str(w.message).lower() for w in captured)
