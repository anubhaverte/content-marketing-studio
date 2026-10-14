"""Pydantic models for layouts, themes, people and the merged Design Spec.

This file is the TEAM CONTRACT. Rules:
- Lengths are in millimeters (mm). Font sizes are in points (pt).
- Layout files use theme token names for colors (e.g. "primary"), never hex codes.
- Theme files use hex colors (e.g. "#1F6FEB").
- Every model forbids unknown fields, so a typo like "dsh" gives a clear error
  instead of being silently ignored.
"""
import re
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    model_validator,
)

from app.spec.constants import (
    BLEED_MM,
    CARD_H_MM,
    CARD_W_MM,
    DEFAULT_ROLES,
    SAFE_MM,
    SCHEMA_VERSION,
    THEME_TOKENS,
)

HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
ELEMENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class StrictModel(BaseModel):
    """Base class: unknown fields are errors."""
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- colors
def _check_token(value: str) -> str:
    """Layout colors must be a theme token name or 'none'."""
    if value == "none" or value in THEME_TOKENS:
        return value
    if HEX_RE.match(value):
        raise ValueError(
            f"hex color '{value}' is not allowed in a layout. "
            f"Use a theme token instead: {', '.join(THEME_TOKENS)}"
        )
    raise ValueError(
        f"'{value}' is not a valid color token. Use one of: {', '.join(THEME_TOKENS)} or 'none'"
    )


def _check_hex(value: str) -> str:
    """Theme colors must be hex."""
    if not HEX_RE.match(value):
        raise ValueError(f"'{value}' is not a valid hex color (use #RGB, #RRGGBB or #RRGGBBAA)")
    return value


LayoutColor = Annotated[str, AfterValidator(_check_token)]
HexColor = Annotated[str, AfterValidator(_check_hex)]


class GradientFill(StrictModel):
    """A gradient fill. Stops use theme tokens: [[0.0, "primary"], [1.0, "background"]]."""
    gradient: Literal["linear"]
    angle: float = 0
    stops: list[tuple[float, LayoutColor]] = Field(min_length=2)

    @model_validator(mode="after")
    def _offsets_in_range(self) -> "GradientFill":
        for offset, _color in self.stops:
            if not 0 <= offset <= 1:
                raise ValueError(f"gradient stop offset {offset} must be between 0 and 1")
        return self


def _fill_kind(value: Any) -> str:
    return "gradient" if isinstance(value, (dict, GradientFill)) else "token"


Fill = Annotated[
    Union[
        Annotated[LayoutColor, Tag("token")],
        Annotated[GradientFill, Tag("gradient")],
    ],
    Discriminator(_fill_kind),
]


# -------------------------------------------------------- layout elements
ElementIdField = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_-]*$")


class RectEl(StrictModel):
    type: Literal["rect"]
    id: Optional[str] = ElementIdField
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)
    fill: Fill = "none"
    stroke: LayoutColor = "none"
    stroke_width: float = Field(default=0, ge=0)
    radius: float = Field(default=0, ge=0)
    dash: Optional[list[float]] = None
    opacity: float = Field(default=1, ge=0, le=1)


class LineEl(StrictModel):
    type: Literal["line"]
    id: Optional[str] = ElementIdField
    x1: float
    y1: float
    x2: float
    y2: float
    stroke: LayoutColor
    stroke_width: float = Field(default=0.3, gt=0)
    dash: Optional[list[float]] = None
    opacity: float = Field(default=1, ge=0, le=1)


class CircleEl(StrictModel):
    type: Literal["circle"]
    id: Optional[str] = ElementIdField
    cx: float
    cy: float
    r: float = Field(gt=0)
    fill: Fill = "none"
    stroke: LayoutColor = "none"
    stroke_width: float = Field(default=0, ge=0)
    opacity: float = Field(default=1, ge=0, le=1)


class TextEl(StrictModel):
    type: Literal["text"]
    id: Optional[str] = ElementIdField
    field: Optional[str] = None   # data field to show, e.g. "name"
    value: Optional[str] = None   # or fixed text
    x: float
    y: float
    w: float = Field(gt=0)
    font: Literal["heading", "body"] = "body"
    color: LayoutColor = "text"
    max_font: float = Field(default=14, gt=0)   # pt
    min_font: float = Field(default=8, gt=0)    # pt
    max_lines: int = Field(default=1, ge=1)
    align: Literal["left", "center", "right"] = "left"
    bold: bool = False
    uppercase: bool = False

    @model_validator(mode="after")
    def _field_or_value(self) -> "TextEl":
        if (self.field is None) == (self.value is None):
            raise ValueError("a text element needs exactly one of 'field' or 'value'")
        if self.min_font > self.max_font:
            raise ValueError(f"min_font ({self.min_font}) must not be larger than max_font ({self.max_font})")
        return self


class PhotoEl(StrictModel):
    type: Literal["photo"]
    id: Optional[str] = ElementIdField
    field: str = "photo"
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)
    shape: Literal["rect", "rounded", "circle"] = "rect"
    radius: float = Field(default=0, ge=0)


class LogoEl(StrictModel):
    type: Literal["logo"]
    id: Optional[str] = ElementIdField
    src: str                      # logo id, e.g. "acm_nitsurat"
    x: float
    y: float
    w: float = Field(gt=0)
    h: Optional[float] = Field(default=None, gt=0)   # omit to follow the logo's aspect ratio
    fit: Literal["contain"] = "contain"


class RoleBadgeEl(StrictModel):
    type: Literal["role_badge"]
    id: Optional[str] = ElementIdField
    field: str = "role"
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)
    text_color: LayoutColor = "background"


class QrEl(StrictModel):
    type: Literal["qr"]
    id: Optional[str] = ElementIdField
    field: str = "qr_url"
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)
    fg: LayoutColor = "text"
    bg: LayoutColor = "background"

    @model_validator(mode="after")
    def _square(self) -> "QrEl":
        if abs(self.w - self.h) > 1e-9:
            raise ValueError(f"a QR code must be square, but w={self.w} and h={self.h}")
        return self


class SvgAssetEl(StrictModel):
    type: Literal["svg_asset"]
    id: Optional[str] = ElementIdField
    src: str                      # file name in assets/art
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)


Element = Annotated[
    Union[RectEl, LineEl, CircleEl, TextEl, PhotoEl, LogoEl, RoleBadgeEl, QrEl, SvgAssetEl],
    Field(discriminator="type"),
]


def _validate_unique_ids(elements: list[Any]) -> None:
    seen = set()
    for el in elements:
        el_id = getattr(el, "id", None)
        if el_id is not None:
            if el_id in seen:
                raise ValueError(f"duplicate element id '{el_id}'")
            seen.add(el_id)


# ------------------------------------------------------------ page, layout
class PageSpec(StrictModel):
    width_mm: float = Field(default=CARD_W_MM, gt=0)
    height_mm: float = Field(default=CARD_H_MM, gt=0)
    bleed_mm: float = Field(default=BLEED_MM, ge=0)
    safe_mm: float = Field(default=SAFE_MM, ge=0)

    @property
    def canvas_w_mm(self) -> float:
        return self.width_mm + 2 * self.bleed_mm

    @property
    def canvas_h_mm(self) -> float:
        return self.height_mm + 2 * self.bleed_mm


class Layout(StrictModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    page: PageSpec = PageSpec()
    elements: list[Element] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> "Layout":
        _validate_unique_ids(self.elements)
        return self


# ------------------------------------------------------------------- theme
class ThemeColors(StrictModel):
    background: HexColor
    primary: HexColor
    secondary: HexColor
    accent: HexColor
    text: HexColor


class ThemeFonts(StrictModel):
    heading: str
    body: str


class Theme(StrictModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    colors: ThemeColors
    fonts: ThemeFonts
    role_colors: dict[str, HexColor]

    @model_validator(mode="after")
    def _default_roles_present(self) -> "Theme":
        missing = [r for r in DEFAULT_ROLES if r not in self.role_colors]
        if missing:
            raise ValueError(f"role_colors is missing: {', '.join(missing)}")
        return self


# -------------------------------------------------------------- data models
class Person(StrictModel):
    """One row of participant data. Only the name is required."""
    name: str = Field(min_length=1)
    role: str = "participant"      # checked against roles.json in Phase 3
    id: Optional[str] = None
    team: Optional[str] = None
    email: Optional[str] = None
    photo: Optional[str] = None    # file name of the photo
    qr_url: Optional[str] = None
    extra: dict[str, str] = Field(default_factory=dict)

    def get_field(self, name: str) -> Optional[str]:
        """Return the value of a known attribute or extra[name], or None."""
        known = ("name", "role", "id", "team", "email", "photo", "qr_url")
        if name in known:
            return getattr(self, name)
        return self.extra.get(name, None)


class EventInfo(StrictModel):
    event_name: Optional[str] = None
    tagline: Optional[str] = None
    venue: Optional[str] = None
    dates: Optional[str] = None


class BrandKit(StrictModel):
    logos: dict[str, str]          # logo id -> file path
    primary_color: Optional[HexColor] = None
    secondary_color: Optional[HexColor] = None
    fonts: Optional[ThemeFonts] = None

    @model_validator(mode="after")
    def _both_logos(self) -> "BrandKit":
        missing = [k for k in ("acm_nitsurat", "svnit") if k not in self.logos]
        if missing:
            raise ValueError(f"brand kit must include logos: {', '.join(missing)}")
        return self


class PrintSettings(StrictModel):
    """Print production and export settings."""
    dpi: int = Field(default=300)
    include_bleed: bool = True
    crop_marks: bool = False
    color_mode: Literal["rgb", "grayscale"] = "rgb"

    @model_validator(mode="after")
    def _valid_dpi(self) -> "PrintSettings":
        if self.dpi not in (150, 300, 600):
            raise ValueError(f"dpi must be one of 150, 300, 600; got {self.dpi}")
        return self


class DesignSpec(StrictModel):
    """Layout + theme + brand kit + event info merged. The renderer reads this (Phase 2)."""
    schema_version: str = SCHEMA_VERSION
    layout_name: str
    theme_name: str
    page: PageSpec
    theme: Theme
    elements: list[Element]
    brand: BrandKit
    event: EventInfo = EventInfo()
    print_settings: PrintSettings = Field(default_factory=PrintSettings)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> "DesignSpec":
        _validate_unique_ids(self.elements)
        return self


# ------------------------------------------------------------- patch models
class PatchOp(StrictModel):
    """A patch operation for modifying a DesignSpec."""
    op: Literal["set", "add", "remove"]
    path: str
    value: Any = None

    @model_validator(mode="after")
    def _check_op_value(self) -> "PatchOp":
        if self.op in ("set", "add"):
            if "value" not in self.model_fields_set:
                raise ValueError(f"op '{self.op}' requires 'value' to be provided")
        elif self.op == "remove":
            if "value" in self.model_fields_set and self.value is not None:
                raise ValueError("op 'remove' must not provide a value")

        if self.path == "schema_version" or self.path.startswith("schema_version."):
            raise ValueError("patching 'schema_version' is not allowed")
        return self
