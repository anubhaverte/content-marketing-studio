"""
design_tools/config.py
======================
Central configuration constants and design rules for the ID Card Design Tool.
Track 4: Content and Marketing Studio | ACM NIT Surat & SVNIT (Incursion Hackathon)

This module defines all authoritative dimension parameters, safe margins,
accessibility thresholds, allowed schema tokens, and role taxonomy for
validating layout and theme specifications.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Set, FrozenSet


# ==============================================================================
# 1. PATH CONFIGURATION
# ==============================================================================

# studio/ base directory
STUDIO_DIR: Path = Path(__file__).resolve().parent.parent
REPO_ROOT: Path = STUDIO_DIR.parent if STUDIO_DIR.name == "studio" else STUDIO_DIR

LAYOUTS_DIR: Path = STUDIO_DIR / "backend" / "app" / "templates" / "layouts"
THEMES_DIR: Path = STUDIO_DIR / "backend" / "app" / "templates" / "themes"
LOGOS_DIR: Path = STUDIO_DIR / "assets" / "logos"
FONTS_DIR: Path = STUDIO_DIR / "assets" / "fonts"
SAMPLE_DATA_DIR: Path = STUDIO_DIR / "sample_data"
DOCS_DIR: Path = STUDIO_DIR / "docs"
DESIGN_TOOLS_DIR: Path = STUDIO_DIR / "design_tools"


# ==============================================================================
# 2. PHYSICAL DIMENSIONS & CANVAS (in millimeters, mm)
# ==============================================================================

# Card Trim Dimensions (Default specification)
CARD_TRIM_WIDTH_MM: float = 54.0
CARD_TRIM_HEIGHT_MM: float = 86.0  # Default per specification (see conflicts below)

# Alternative ISO/IEC 7810 ID-1 standard height
CARD_TRIM_HEIGHT_ISO_MM: float = 85.60
CARD_TRIM_WIDTH_ISO_MM: float = 53.98

# Print Bleed (3 mm on all 4 sides: top, bottom, left, right)
BLEED_MM: float = 3.0

# Total Canvas Dimensions including 3 mm bleed
# Canvas coordinates start at top-left corner (0.0, 0.0)
CANVAS_WIDTH_MM: float = CARD_TRIM_WIDTH_MM + (2 * BLEED_MM)    # 60.0 mm
CANVAS_HEIGHT_MM: float = CARD_TRIM_HEIGHT_MM + (2 * BLEED_MM)  # 92.0 mm

# Alternative Canvas Height with ISO 85.6 mm trim
CANVAS_HEIGHT_ISO_MM: float = CARD_TRIM_HEIGHT_ISO_MM + (2 * BLEED_MM)  # 91.6 mm

# Trim Area Bounding Box on Canvas coordinates (x: [3, 57], y: [3, 89])
TRIM_X_MIN: float = BLEED_MM                          # 3.0 mm
TRIM_X_MAX: float = CANVAS_WIDTH_MM - BLEED_MM        # 57.0 mm
TRIM_Y_MIN: float = BLEED_MM                          # 3.0 mm
TRIM_Y_MAX: float = CANVAS_HEIGHT_MM - BLEED_MM       # 89.0 mm


# ==============================================================================
# 3. SAFE AREA SPECIFICATION (in millimeters, mm)
# ==============================================================================
# All critical elements (text, logos, photos, QR codes, badges) MUST reside
# strictly within this bounding box to guarantee safety against cutting tolerances.

# Safe margin measured from canvas boundary (default: 7.0 mm)
# Note: 7.0 mm from canvas edge = 4.0 mm from trim line (7 - 3 = 4 mm)
SAFE_MARGIN_FROM_CANVAS_MM: float = 7.0

# Alternative safe margin (4.0 mm from canvas edge if interpreted literally)
SAFE_MARGIN_ALT_CANVAS_MM: float = 4.0

# Default Safe Area Bounding Box on Canvas coordinates:
# x: 7.0 to 53.0 mm (width = 46.0 mm)
# y: 7.0 to 85.0 mm (height = 78.0 mm)
SAFE_AREA_X_MIN: float = 7.0
SAFE_AREA_X_MAX: float = 53.0  # CANVAS_WIDTH_MM - SAFE_MARGIN_FROM_CANVAS_MM
SAFE_AREA_Y_MIN: float = 7.0
SAFE_AREA_Y_MAX: float = 85.0  # CANVAS_HEIGHT_MM - SAFE_MARGIN_FROM_CANVAS_MM

SAFE_AREA_WIDTH_MM: float = SAFE_AREA_X_MAX - SAFE_AREA_X_MIN   # 46.0 mm
SAFE_AREA_HEIGHT_MM: float = SAFE_AREA_Y_MAX - SAFE_AREA_Y_MIN  # 78.0 mm


# ==============================================================================
# 4. QR CODE & LOGO CONSTRAINTS
# ==============================================================================

# Minimum QR code dimensions for reliable optical scanning (12 x 12 mm)
MIN_QR_SIZE_MM: float = 12.0
MIN_QR_WIDTH_MM: float = 12.0
MIN_QR_HEIGHT_MM: float = 12.0

# Required institutional logos that must be present on every layout
REQUIRED_LOGOS: Tuple[str, ...] = (
    "acm_nit_surat",
    "svnit",
)

# Mandatory fit mode for logo elements (must never stretch)
ALLOWED_LOGO_FITS: Tuple[str, ...] = (
    "contain",
)


# ==============================================================================
# 5. ACCESSIBILITY & CONTRAST (WCAG 2.1)
# ==============================================================================

# Minimum WCAG AA contrast ratio for regular body and title text
MIN_CONTRAST_RATIO: float = 4.5  # 4.5:1 minimum contrast

# Enhanced WCAG AAA contrast ratio target
MIN_CONTRAST_RATIO_AAA: float = 7.0


# ==============================================================================
# 6. ALLOWED SCHEMA TOKENS (ELEMENT TYPES & NAMED COLORS)
# ==============================================================================

# Exactly 9 allowed element types in Layout JSON schema:
ALLOWED_ELEMENT_TYPES: FrozenSet[str] = frozenset({
    "rect",
    "line",
    "circle",
    "text",
    "photo",
    "logo",
    "role_badge",
    "qr",
    "svg_asset",
})

# Exactly 7 semantic color tokens permitted in Layout JSON files:
# Hex colors are strictly prohibited in layouts and belong in themes only.
ALLOWED_COLOR_NAMES: FrozenSet[str] = frozenset({
    "primary",
    "secondary",
    "background",
    "text",
    "muted",
    "accent",
    "role",  # Resolves dynamically to the role-specific palette
})

# Allowed attendee roles
ALLOWED_ROLES: FrozenSet[str] = frozenset({
    "participant",
    "organizer",
    "mentor",
})

# Allowed photo crop shapes
ALLOWED_PHOTO_SHAPES: FrozenSet[str] = frozenset({
    "rect",
    "circle",
    "rounded_rect",
})

# Allowed text alignments
ALLOWED_TEXT_ALIGNS: FrozenSet[str] = frozenset({
    "left",
    "center",
    "right",
})


# ==============================================================================
# 7. ELEMENT PROPERTY SCHEMAS (MANDATORY & OPTIONAL KEYS)
# ==============================================================================

ELEMENT_PROPERTY_SPECS: Dict[str, Dict[str, Any]] = {
    "rect": {
        "required": {"type", "x", "y", "w", "h"},
        "optional": {"fill", "stroke", "stroke_width", "rx", "ry", "opacity"},
        "description": "Geometric rectangle / container block",
    },
    "line": {
        "required": {"type", "x1", "y1", "x2", "y2"},
        "optional": {"stroke", "stroke_width", "dash_pattern", "opacity"},
        "description": "Geometric separator or accent line",
    },
    "circle": {
        "required": {"type", "cx", "cy", "r"},
        "optional": {"fill", "stroke", "stroke_width", "opacity"},
        "description": "Geometric circle or decorative disc",
    },
    "text": {
        "required": {"type", "field", "x", "y", "w", "max_lines", "min_font", "max_font", "align"},
        "optional": {"color", "font_style", "letter_spacing", "line_height", "transform"},
        "description": "Dynamic text bound to data field with auto-fit bounds",
    },
    "photo": {
        "required": {"type", "field", "x", "y", "w", "h", "shape"},
        "optional": {"border_color", "border_width", "aspect_ratio", "fit"},
        "description": "Attendee photo box with clipping shape",
    },
    "logo": {
        "required": {"type", "src", "x", "y", "w", "fit"},
        "optional": {"h", "align"},
        "description": "Institutional partner logo with contain fit",
    },
    "role_badge": {
        "required": {"type", "field", "x", "y", "w", "h"},
        "optional": {"shape", "color", "background", "border_width", "border_color", "font_size"},
        "description": "Accessible role badge with distinct monochrome geometry & label",
    },
    "qr": {
        "required": {"type", "field", "x", "y", "w", "h"},
        "optional": {"color", "background", "error_correction"},
        "description": "Security QR verification matrix (min 12x12 mm)",
    },
    "svg_asset": {
        "required": {"type", "src", "x", "y", "w", "h"},
        "optional": {"fit", "opacity", "tint"},
        "description": "Decorative vector graphic or motif",
    },
}


# ==============================================================================
# 8. SPECIFICATION CONFLICTS REGISTRY
# ==============================================================================
# If rules conflict across source documents, explicit constants and defaults
# are tracked here rather than guessing.

SPEC_CONFLICTS: Dict[str, Dict[str, Any]] = {
    "CARD_HEIGHT": {
        "default": CARD_TRIM_HEIGHT_MM,       # 86.0 mm (per task prompt)
        "alternative": CARD_TRIM_HEIGHT_ISO_MM, # 85.60 mm (ISO/IEC 7810 ID-1 standard)
        "description": (
            "Card trim height: 86.0 mm is specified in the task prompt (giving a "
            "60 x 92 mm canvas with 3 mm bleed). The official ISO/IEC 7810 ID-1 "
            "standard card height is 85.60 mm (giving 91.6 mm canvas). "
            "Default selected: 86.0 mm."
        ),
    },
    "SAFE_MARGIN": {
        "default": SAFE_MARGIN_FROM_CANVAS_MM, # 7.0 mm from canvas edge
        "alternative": 4.0,                    # 4.0 mm
        "description": (
            "Safe margin: The prompt specifies safe area x from 7 to 53, y from 7 to 85, "
            "which corresponds to a 7.0 mm margin from the canvas boundary. Note that with "
            "a 3.0 mm bleed, 7.0 mm from canvas boundary equals exactly 4.0 mm from the "
            "trim line (7 - 3 = 4 mm). If another document specifies 4.0 mm safe margin, "
            "it refers to distance from trim line, or an alternative 4 mm canvas margin. "
            "Default selected: 7.0 mm from canvas boundary (x: 7..53 mm, y: 7..85 mm)."
        ),
    },
}


# ==============================================================================
# 9. VALIDATION HELPER FUNCTIONS
# ==============================================================================

def is_valid_element_type(elem_type: str) -> bool:
    """Check if the given element type is recognized in the layout schema."""
    return elem_type in ALLOWED_ELEMENT_TYPES


def is_valid_color_name(color_name: str) -> bool:
    """Check if the given color name is one of the 7 allowed semantic layout colors."""
    return color_name in ALLOWED_COLOR_NAMES


def is_valid_role(role_name: str) -> bool:
    """Check if the given role is valid."""
    return role_name in ALLOWED_ROLES


def is_within_safe_area(x: float, y: float, w: float = 0.0, h: float = 0.0) -> bool:
    """
    Validate whether a bounding box falls strictly inside the safe area.
    Coordinates are in mm starting at canvas top-left (0, 0).
    """
    x_max = x + w
    y_max = y + h
    return (
        x >= SAFE_AREA_X_MIN and
        x_max <= SAFE_AREA_X_MAX and
        y >= SAFE_AREA_Y_MIN and
        y_max <= SAFE_AREA_Y_MAX
    )


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Convert #RRGGBB or #RGB to (R, G, B) tuple of ints in [0, 255]."""
    cleaned = hex_code.strip().lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join([c * 2 for c in cleaned])
    if len(cleaned) != 6:
        raise ValueError(f"Invalid hex color code: '{hex_code}'")
    return int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16)


def relative_luminance(r: int, g: int, b: int) -> float:
    """
    Calculate WCAG 2.1 relative luminance for an sRGB color.
    Formula: https://www.w3.org/WAI/GL/wiki/Relative_luminance
    """
    def channel_linear(c_byte: int) -> float:
        c = c_byte / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = channel_linear(r)
    g_lin = channel_linear(g)
    b_lin = channel_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(hex1: str, hex2: str) -> float:
    """
    Calculate the WCAG contrast ratio between two hex color codes.
    Returns a float in [1.0, 21.0].
    """
    rgb1 = hex_to_rgb(hex1)
    rgb2 = hex_to_rgb(hex2)
    l1 = relative_luminance(*rgb1)
    l2 = relative_luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def is_wcag_aa_compliant(text_hex: str, bg_hex: str, min_ratio: float = MIN_CONTRAST_RATIO) -> bool:
    """Check if the contrast ratio between text and background satisfies WCAG AA (>= 4.5:1)."""
    return contrast_ratio(text_hex, bg_hex) >= min_ratio


# ==============================================================================
# 10. SELF-TEST & SUMMARY CLI
# ==============================================================================

def print_summary() -> None:
    """Print configuration parameters, bounds, and rule constants."""
    print("=" * 70)
    print("ID CARD DESIGN TOOL - CONFIGURATION SPECIFICATION")
    print("=" * 70)
    print(f"Canvas Size       : {CANVAS_WIDTH_MM} x {CANVAS_HEIGHT_MM} mm (with {BLEED_MM} mm bleed)")
    print(f"Card Trim Size    : {CARD_TRIM_WIDTH_MM} x {CARD_TRIM_HEIGHT_MM} mm")
    print(f"Safe Area Bounds  : x: [{SAFE_AREA_X_MIN}, {SAFE_AREA_X_MAX}] mm | y: [{SAFE_AREA_Y_MIN}, {SAFE_AREA_Y_MAX}] mm")
    print(f"Safe Area Size    : {SAFE_AREA_WIDTH_MM} x {SAFE_AREA_HEIGHT_MM} mm")
    print(f"Min QR Code Size  : {MIN_QR_SIZE_MM} x {MIN_QR_SIZE_MM} mm")
    print(f"Min WCAG Contrast : {MIN_CONTRAST_RATIO}:1")
    print(f"Allowed Elements  : {', '.join(sorted(ALLOWED_ELEMENT_TYPES))}")
    print(f"Allowed Colors    : {', '.join(sorted(ALLOWED_COLOR_NAMES))}")
    print(f"Allowed Roles     : {', '.join(sorted(ALLOWED_ROLES))}")
    print(f"Required Logos    : {', '.join(REQUIRED_LOGOS)}")
    print("-" * 70)
    print("SPECIFICATION CONFLICTS REGISTERED:")
    for k, v in SPEC_CONFLICTS.items():
        print(f"  * {k}: default={v['default']}, alternative={v['alternative']}")
        print(f"    Note: {v['description']}")
    print("=" * 70)


if __name__ == "__main__":
    print_summary()
