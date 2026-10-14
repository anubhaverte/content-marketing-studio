"""Asset and path helpers for resolving repo-relative asset files."""
from pathlib import Path

from app.config import ROOT


def asset_path(relative: str) -> Path:
    """Resolve a repo-relative POSIX path against the repository root.

    Raises:
        ValueError: If the path is absolute or contains parent directory traversal ('..').
    """
    if not relative:
        raise ValueError("Relative path cannot be empty")

    norm = relative.replace("\\", "/").strip()
    if norm.startswith("/") or ":" in norm:
        raise ValueError(f"Path must be repo-relative, not absolute: {relative}")

    parts = norm.split("/")
    if ".." in parts:
        raise ValueError(f"Path cannot contain directory traversal ('..'): {relative}")

    return ROOT / norm
