"""Validated export options that can be serialized for the API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ExportSettings:
    """Options controlling output format, resolution, orientation, and bleed."""

    format: str = "svg"
    dpi: int = 300
    orientation: str = "portrait"
    bleed: bool = True

    def __post_init__(self) -> None:
        """Reject unsupported or malformed settings immediately."""
        if self.format not in {"svg", "pdf", "png"}:
            raise ValueError("format must be one of: svg, pdf, png")
        if isinstance(self.dpi, bool) or not isinstance(self.dpi, int) or self.dpi <= 0:
            raise ValueError("dpi must be a positive integer")
        if self.orientation not in {"portrait", "landscape"}:
            raise ValueError("orientation must be 'portrait' or 'landscape'")
        if not isinstance(self.bleed, bool):
            raise ValueError("bleed must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-friendly values for an API request or batch report."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExportSettings:
        """Build settings from an API-style mapping."""
        if not isinstance(data, Mapping):
            raise ValueError("settings must be an object")
        allowed = {"format", "dpi", "orientation", "bleed"}
        unexpected = set(data) - allowed
        if unexpected:
            raise ValueError(f"unknown export setting(s): {', '.join(sorted(unexpected))}")
        return cls(**dict(data))


@dataclass(frozen=True)
class PrintSheetSettings:
    """Options controlling print-sheet layout and page annotations."""

    orientation: str = "portrait"
    bleed: bool = True
    crop_marks: bool = True
    page_labels: bool = True
    group_by_role: bool = False

    def __post_init__(self) -> None:
        """Reject malformed print-sheet options."""
        if self.orientation not in {"portrait", "landscape"}:
            raise ValueError("orientation must be 'portrait' or 'landscape'")
        for name in ("bleed", "crop_marks", "page_labels", "group_by_role"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-friendly print-sheet options."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PrintSheetSettings:
        """Build validated print-sheet options from an API-style mapping."""
        if not isinstance(data, Mapping):
            raise ValueError("settings must be an object")
        allowed = {"orientation", "bleed", "crop_marks", "page_labels", "group_by_role"}
        unexpected = set(data) - allowed
        if unexpected:
            raise ValueError(f"unknown print-sheet setting(s): {', '.join(sorted(unexpected))}")
        return cls(**dict(data))
