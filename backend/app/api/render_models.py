"""Pydantic API request and response models for render endpoints.

Owned by Person 2 per docs/OWNERS.json.
"""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.spec.schema import DesignSpec, Person


class StrictModel(BaseModel):
    """Base API model forbidding unknown fields."""
    model_config = ConfigDict(extra="forbid")


class BatchExportSettings(BaseModel):
    """Export configuration for batch rendering."""
    model_config = ConfigDict(extra="ignore")

    format: Literal["pdf", "png", "svg"] = "pdf"
    dpi: int = Field(default=300, gt=0)
    orientation: Literal["portrait", "landscape"] = "portrait"
    bleed: bool = True


class RenderBatchRequest(StrictModel):
    """Request model for batch card rendering and exporting."""
    spec: DesignSpec
    people: list[Person]
    settings: Optional[BatchExportSettings] = None
    format: Optional[Literal["pdf", "png", "svg", "zip"]] = None
    collate_pdf: bool = False
    skipped_rows: list[dict[str, Any]] = Field(default_factory=list)
    return_json: bool = False


class RenderBatchResponse(StrictModel):
    """Structured JSON response containing batch report and base64 archive."""
    totals: dict[str, int]
    people: list[dict[str, Any]]
    skipped_rows: list[dict[str, Any]]
    settings: dict[str, Any]
    archive_base64: str
    filename: str
    media_type: str


class RenderPrintSheetRequest(StrictModel):
    """Request model for generating an imposed A4/A3 print sheet PDF."""
    spec: DesignSpec
    people: list[Person]
    page: Literal["A4", "A3"] = "A4"
    crop_marks: bool = True

