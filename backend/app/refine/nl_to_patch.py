"""Natural-language refinement: AI turns a request into a small Design Spec patch."""
from typing import Any

from app.refine.patch import apply_patch  # re-export single source of truth


def nl_to_patch(request_text: str, spec: Any) -> list[dict[str, Any]]:
    """Ask the AI for a patch like [{'op': 'set', 'path': 'elements.0.y', 'value': 4}].

    Implemented in Phase 7.
    """
    raise NotImplementedError("Phase 7: Ask the AI for a patch like [{'op': 'set', 'path': 'elements'}]")
