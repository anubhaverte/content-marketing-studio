"""Draft generation routes."""
from typing import Optional

from fastapi import APIRouter, Query

from app.api.models import DraftsRequest, DraftsResponse
from app.generator.drafts import generate_drafts

router = APIRouter(tags=["drafts"])


@router.post("/drafts", response_model=DraftsResponse)
def create_drafts(
    payload: DraftsRequest,
    mock: Optional[bool] = Query(default=None),
) -> DraftsResponse:
    """Generate candidate DesignSpecs for an event brief.

    Discovers catalog layouts and themes, ranks combinations according to
    the Brief style hint, and returns up to `payload.count` distinct candidates.

    Preserves mock=True behavior when requested or when running variations.
    """
    # If caller explicitly asked for mock or did not disable variations
    allow_variations = True if (mock is not False) else False

    drafts, is_mock = generate_drafts(
        brief=payload.brief,
        event=payload.event,
        count=payload.count,
        allow_theme_variations=allow_variations,
    )

    # Determine mock flag in response:
    # If ?mock=true is explicitly requested, response has mock=True.
    # If ?mock=false is explicitly requested, response has mock=False.
    # Otherwise, if catalog could not satisfy full distinct count without color variants, mock=True.
    response_mock = True if (mock is True or (mock is None and is_mock)) else (False if mock is False else is_mock)

    return DraftsResponse(
        drafts=drafts,
        mock=response_mock,
    )
