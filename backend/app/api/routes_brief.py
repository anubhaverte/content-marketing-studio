"""Event brief extraction routes."""
from typing import Optional

from fastapi import APIRouter, Query

from app.api.models import BriefRequest, BriefResponse, Question
from app.brief.extract import extract_brief
from app.brief.missing_info import find_missing
from app.brief.questions import build_questions

router = APIRouter(tags=["brief"])


@router.post("/brief", response_model=BriefResponse)
def create_brief(
    payload: BriefRequest,
    mock: Optional[bool] = Query(default=None),
) -> BriefResponse:
    """Extract a structured brief from user description.

    Uses Gemini structured extraction when GEMINI_API_KEY is configured.
    Falls back gracefully and deterministically to missing-question collection
    when offline, preserving full API compatibility.

    Query parameter ?mock=true or ?mock=false can explicitly control mock mode.
    """
    # If caller explicitly asked for mock
    if mock is True:
        brief, _ = extract_brief(payload.text, provider=None)
        missing = find_missing(brief)
        question_dicts = build_questions(missing)
        questions = [Question.model_validate(q) for q in question_dicts]
        return BriefResponse(
            brief=brief,
            missing=missing,
            questions=questions,
            mock=True,
        )

    # Perform extraction via service (provider injection or env-based Gemini)
    brief, is_fallback = extract_brief(payload.text)
    missing = find_missing(brief)
    question_dicts = build_questions(missing)
    questions = [Question.model_validate(q) for q in question_dicts]

    # If mock query parameter was not explicitly passed:
    # If extraction was fallback, set mock=True to preserve API contract.
    # If extraction succeeded with AI, set mock=False.
    response_mock = True if (mock is not False and is_fallback) else False

    return BriefResponse(
        brief=brief,
        missing=missing,
        questions=questions,
        mock=response_mock,
    )
