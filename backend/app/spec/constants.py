"""Fixed numbers used across the project. Everything is in millimeters (mm)."""

SCHEMA_VERSION = "1.0"

CARD_W_MM = 54        # trim width (final card)
CARD_H_MM = 86        # trim height (final card)
BLEED_MM = 3          # extra area beyond the trim line, so no white edge shows
SAFE_MM = 4           # keep text and logos this far inside the trim line
CANVAS_W_MM = CARD_W_MM + 2 * BLEED_MM   # 60
CANVAS_H_MM = CARD_H_MM + 2 * BLEED_MM   # 92

# Safe area in CANVAS coordinates (origin = top-left of the 60 x 92 canvas):
# x0, y0, x1, y1
SAFE_BOX = (
    BLEED_MM + SAFE_MM,
    BLEED_MM + SAFE_MM,
    CANVAS_W_MM - BLEED_MM - SAFE_MM,
    CANVAS_H_MM - BLEED_MM - SAFE_MM,
)  # (7, 7, 53, 85)

MM_PER_PT = 0.352778  # 1 point = 0.352778 mm (font sizes in JSON are in pt)
DEFAULT_DPI = 300

# Layouts refer to colors by these names. The theme file maps each name to a hex color.
THEME_TOKENS = ("background", "primary", "secondary", "accent", "text")

# Roles are config-driven (see templates/roles.json). These three must always
# exist in every theme's role_colors. Do not hardcode role logic anywhere else.
DEFAULT_ROLES = ("participant", "organizer", "mentor")
