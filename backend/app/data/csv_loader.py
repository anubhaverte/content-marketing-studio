"""Load participant data from CSV and guess which column is which.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional


def guess_column_mapping(columns: list[str]) -> dict[str, str]:
    """Auto-guess a mapping from CSV column names to card fields (name, role, id, team, email, photo).

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: Auto-guess a mapping from CSV column names to card fields (name, role, id, team, email, photo)")


def load_people_csv(path: Path, mapping: Optional[dict[str, str]] = None) -> list[dict[str, Any]]:
    """Read the CSV with pandas and return raw rows using the column mapping.

    Implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: Read the CSV with pandas and return raw rows using the column mapping")
