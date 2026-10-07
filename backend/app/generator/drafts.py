"""Pick 3 clearly different layout + theme combinations, deterministically.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional
from app.brief.schema import Brief
from app.spec.schema import DesignSpec


def generate_drafts(brief: Brief, count: int = 3) -> list[DesignSpec]:
    """Each draft must use a different layout AND a different theme. The style hint from the Brief influences the order. The same input always gives the same drafts.

    Implemented in Phase 4.
    """
    raise NotImplementedError("Phase 4: Each draft must use a different layout AND a different theme")
