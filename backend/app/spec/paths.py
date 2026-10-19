"""Asset and path helpers for resolving repo-relative asset files."""
from pathlib import Path

from app.config import ASSETS, BACKEND, ROOT


def asset_path(relative: str) -> Path:
    """Resolve a repo-relative POSIX path against the repository root or asset directories.

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

    # 1. Exact path against repository ROOT
    primary = ROOT / norm
    if primary.is_file():
        return primary

    # 2. Check candidate locations for stripped relative path
    sub = norm
    if sub.startswith("frontend/public/"):
        sub = sub[len("frontend/public/"):]
    elif sub.startswith("assets/"):
        sub = sub[len("assets/"):]

    candidates: list[Path] = [
        ASSETS / sub,
        BACKEND / "app" / "assets" / sub,
        BACKEND / "app" / "assets" / norm,
        ROOT / "frontend" / "public" / sub,
        ROOT / "frontend" / "public" / norm,
        ROOT / "assets" / sub,
    ]

    for cand in candidates:
        if cand.is_file():
            return cand

    # 3. Fallback search by filename in known asset directories
    filename = Path(norm).name
    search_dirs = [
        ASSETS / "art",
        ASSETS / "logos",
        BACKEND / "app" / "assets" / "art",
        BACKEND / "app" / "assets" / "logos",
        ROOT / "assets" / "art",
        ROOT / "assets" / "logos",
        ROOT / "frontend" / "public" / "art",
        ROOT / "frontend" / "public" / "logos",
    ]
    for d in search_dirs:
        cand = d / filename
        if cand.is_file():
            return cand

    # If not found anywhere, return the primary candidate so callers get standard Path
    return primary

