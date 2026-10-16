"""Find what is still missing from an attendee card Brief using plain code (not AI)."""
from typing import Optional

from app.brief.schema import Brief

# Required fields for an id_card brief according to project specifications
REQUIRED_ID_CARD_FIELDS = [
    "event_name",
    "dates",
    "venue",
    "roles",
    "fields_to_show",
]

OPTIONAL_ID_CARD_FIELDS = [
    "tagline",
    "card_size",
    "orientation",
    "style_hint",
    "lanyard_hole",
]


def find_missing(brief: Brief) -> list[str]:
    """Compare the Brief to required fields for its design type and return missing field names.

    Pure deterministic code: does not use AI.
    """
    missing: list[str] = []

    # 1. Event Name
    if not brief.event_name or not brief.event_name.strip():
        missing.append("event_name")

    # 2. Tagline (optional but prompted if event_name is present and tagline is not)
    if not brief.tagline:
        missing.append("tagline")

    # 3. Dates
    if not brief.dates or not brief.dates.strip():
        missing.append("dates")

    # 4. Venue
    if not brief.venue or not brief.venue.strip():
        missing.append("venue")

    # 5. Roles
    if not brief.roles or len(brief.roles) == 0:
        missing.append("roles")

    # 6. Fields to show on card
    if not brief.fields_to_show or len(brief.fields_to_show) == 0:
        missing.append("fields_to_show")

    return missing
