"""Pydantic API request and response models representing the shared contract."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.brief.schema import Brief
from app.spec.schema import DesignSpec, EventInfo, PatchOp, Person


class StrictModel(BaseModel):
    """Base API model forbidding unknown fields."""
    model_config = ConfigDict(extra="forbid")


class Question(StrictModel):
    """A clarifying question for missing brief details."""
    field: str
    text: str
    kind: Literal["text", "choice", "multi_choice", "number", "boolean"]
    options: Optional[list[str]] = None
    default: Optional[Any] = None
    skippable: bool = True


class BriefRequest(StrictModel):
    """Natural-language text submitted to generate an initial event brief."""
    text: str = Field(min_length=1)


class BriefResponse(StrictModel):
    """Extracted brief, missing fields, and clarifying follow-up questions."""
    brief: Brief
    missing: list[str]
    questions: list[Question]
    mock: bool = False


class DataSummary(StrictModel):
    """Summary of uploaded participant CSV file and column mappings."""
    people_loaded: int
    column_mapping: dict[str, str]
    issues: dict[str, int]
    warnings: list[str]
    mock: bool = False


class DraftsRequest(StrictModel):
    """Request to generate candidate design specs from a brief and event info."""
    brief: Brief = Field(default_factory=Brief)
    event: EventInfo = Field(default_factory=EventInfo)
    count: int = Field(default=3, ge=1, le=9)


class DraftsResponse(StrictModel):
    """Generated candidate design specs."""
    drafts: list[DesignSpec]
    mock: bool = False


class PatchRequest(StrictModel):
    """Request to apply patch operations to an existing DesignSpec."""
    spec: DesignSpec
    ops: list[PatchOp]


class PatchResponse(StrictModel):
    """Patched DesignSpec result."""
    spec: DesignSpec


class RefineRequest(StrictModel):
    """Request to convert natural language instructions into a safe spec patch."""
    spec: DesignSpec
    prompt: str


class RefineResponse(StrictModel):
    """Refined DesignSpec result along with the applied patch operations."""
    spec: DesignSpec
    ops: list[PatchOp]
    summary: str



class RenderPreviewRequest(StrictModel):
    """Contract model for rendering an SVG card preview."""
    spec: DesignSpec
    person: Person
    debug_guides: bool = False


class RenderPreviewResponse(StrictModel):
    """Contract model for SVG card preview output."""
    svg: str
    qa_issues: list[dict[str, Any]]
