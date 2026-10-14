"""SQLite storage for projects, spec versions and brand kits.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional


def init_db(db_path: Path) -> None:
    """Create the SQLite tables if they do not exist.

    Implemented in Phase 7.
    """
    raise NotImplementedError("Phase 7: Create the SQLite tables if they do not exist")


def save_spec_version(project_id: str, spec_json: str) -> int:
    """Save a new version of a Design Spec and return its version number.

    Implemented in Phase 7.
    """
    raise NotImplementedError("Phase 7: Save a new version of a Design Spec and return its version number")


def load_spec_version(project_id: str, version: int) -> str:
    """Load one saved version of a Design Spec (for undo).

    Implemented in Phase 7.
    """
    raise NotImplementedError("Phase 7: Load one saved version of a Design Spec (for undo)")
