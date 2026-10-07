"""Check participant data and report problems. Never fixes names silently.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional


def validate_people(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Flag missing names, unknown roles, duplicate IDs, very long names, missing or unreadable photos. Return a summary like '235 people loaded, 12 have no photo'.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: Flag missing names, unknown roles, duplicate IDs, very long names, missing or unreadable photos")
