"""Brief extraction, missing info detection, and questions package."""
from app.brief.extract import (
    BriefProvider,
    FakeBriefProvider,
    GeminiHttpProvider,
    deterministic_fallback_extraction,
    extract_brief,
)
from app.brief.missing_info import find_missing
from app.brief.questions import build_questions
from app.brief.schema import Brief

__all__ = [
    "Brief",
    "BriefProvider",
    "FakeBriefProvider",
    "GeminiHttpProvider",
    "build_questions",
    "deterministic_fallback_extraction",
    "extract_brief",
    "find_missing",
]
