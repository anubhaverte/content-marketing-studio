"""The Brief: what the AI extracts from the user's plain-English request.

Every field is optional. None means "the user did not say" and becomes a
follow-up question. The AI must never guess a value.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_type: str = "id_card"
    event_name: Optional[str] = None
    tagline: Optional[str] = None
    dates: Optional[str] = None
    venue: Optional[str] = None
    roles: Optional[list[str]] = None
    counts: Optional[dict[str, int]] = None          # e.g. {"participant": 200, "mentor": 20}
    fields_to_show: Optional[list[str]] = None       # e.g. ["name", "role", "id", "photo", "qr"]
    card_size: Optional[str] = None
    orientation: Optional[str] = None
    style_hint: Optional[str] = None                 # e.g. "minimal", "techy"
    lanyard_hole: Optional[bool] = None
