from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from render.photo import resolve_photo_path, photo_markup


def test_photo_traversal_relative_rejected(tmp_path):
    """Verify relative traversal sequences like '../' are rejected."""
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("classified")

    with pytest.raises(ValueError, match="Path traversal detected"):
        resolve_photo_path("../secret.txt", allowed_roots=[photo_dir])


def test_photo_absolute_outside_root_rejected(tmp_path):
    """Verify absolute paths outside allowed roots are rejected."""
    allowed_dir = tmp_path / "photos"
    allowed_dir.mkdir()
    outside_file = tmp_path / "outside.jpg"
    outside_file.write_text("fake image")

    with pytest.raises(ValueError, match="outside allowed directories"):
        resolve_photo_path(outside_file, allowed_roots=[allowed_dir])


def test_photo_valid_within_root(tmp_path):
    """Verify valid photo within root resolves successfully."""
    allowed_dir = tmp_path / "photos"
    allowed_dir.mkdir()
    valid_file = allowed_dir / "portrait.jpg"
    valid_file.write_text("photo data")

    resolved = resolve_photo_path("portrait.jpg", allowed_roots=[allowed_dir])
    assert resolved == valid_file.resolve()
    assert resolved.is_file()


def test_photo_not_found_raises(tmp_path):
    """Verify nonexistent photo raises FileNotFoundError."""
    allowed_dir = tmp_path / "photos"
    allowed_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        resolve_photo_path("nonexistent.jpg", allowed_roots=[allowed_dir])


def test_photo_markup_traversal_rejected():
    """Verify photo_markup directly rejects traversal attempts."""
    with pytest.raises(ValueError, match="Path traversal detected"):
        photo_markup(
            Path("../../secret.jpg"),
            element_id="test",
            x=0,
            y=0,
            width=20,
            height=20,
            shape="circle",
            radius=2,
        )
