"""Turn the user's plain-English request into a Brief using the Gemini API.

STUB: implemented in a later phase (see each function).
"""
from pathlib import Path
from typing import Any, Optional
from app.brief.schema import Brief


def extract_brief(user_text: str) -> Brief:
    """Call Gemini with a strict JSON schema, validate with Pydantic, retry on invalid output. Unknown values stay None. Must fall back to an empty Brief if the AI call fails.

    Implemented in Phase 5.
    """
    raise NotImplementedError("Phase 5: Call Gemini with a strict JSON schema, validate with Pydantic, retry on invalid output")
