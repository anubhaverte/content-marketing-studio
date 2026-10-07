"""Natural-language refinement: AI turns a request into a small Design Spec patch.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional


def nl_to_patch(request_text: str, spec: Any) -> list[dict[str, Any]]:
    """Ask the AI for a patch like [{'op': 'set', 'path': 'elements.0.y', 'value': 4}]. AI can only change fields that exist in the spec.

    Implemented in Phase 7.
    """
    raise NotImplementedError("Phase 7: Ask the AI for a patch like [{'op': 'set', 'path': 'elements")


def apply_patch(spec: Any, patch: list[dict[str, Any]]) -> Any:
    """Validate and apply the patch, then re-run QA. Reject with a message if a rule breaks.

    Implemented in Phase 7.
    """
    raise NotImplementedError("Phase 7: Validate and apply the patch, then re-run QA")
