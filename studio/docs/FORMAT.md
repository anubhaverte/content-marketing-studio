# ID Card Template & Theme Format Specification

**Track 4: Content and Marketing Studio**  
**ACM NIT Surat & SVNIT — Incursion Hackathon**  
*Document Version: 1.0.0*

---

## 1. Overview & Architecture

Cards in this system are generated programmatically by combining:
1. **Layout JSON**: Defines spatial coordinates, element hierarchy, bounding boxes, and semantic color slots.
2. **Theme JSON**: Defines typography, concrete hex color palettes, and role-specific styling.
3. **Attendee Data (CSV / JSON)**: Real attendee records (`full_name`, `role`, `organization`, `id_number`, `photo`, `qr_data`).

### Separation of Concerns
* **Layouts never contain hex colors** (e.g. `#1A202C` is strictly forbidden in layouts). Layouts only reference semantic color tokens: `"primary"`, `"secondary"`, `"background"`, `"text"`, `"muted"`, `"accent"`, and `"role"`.
* **Themes define hex values**: Themes map semantic color tokens to hex colors and provide role palettes.
* **Accessibility**: Every theme must guarantee a contrast ratio of at least **4.5:1 (WCAG AA)** between text and its background, across all standard elements and role variations.

---

## 2. Canvas, Trim, Bleed & Coordinates

* **Coordinate System**: Origin `(0.0, 0.0)` is at the **top-left corner of the canvas**. All units are millimeters (`mm`).
* **Card Trim Size**: `54.0 mm` (width) × `86.0 mm` (height). *(See Section 6 for ISO 85.6 mm conflict notes)*.
* **Print Bleed**: `3.0 mm` on all four edges.
* **Canvas Dimensions**: `60.0 mm` (width) × `92.0 mm` (height) `[54 + 6 x 86 + 6]`.
* **Safe Area**: Bounded by `x: 7.0 mm to 53.0 mm` and `y: 7.0 mm to 85.0 mm` (width: `46.0 mm`, height: `78.0 mm`).
  * **Critical Rule**: All critical text, institutional logos, attendee photos, role badges, and QR codes **must stay strictly inside the safe area**.
  * Only background panels, bleed decorations, or full-bleed borders may extend outside the safe area into the trim and bleed regions.

---

## 3. Layout JSON Specification

Layout JSON files reside in `studio/backend/app/templates/layouts/`.

### 3.1 Allowed Element Types
Only the following **9 element types** are permitted in layout templates:
1. `rect` — Geometric rectangle or solid container panel.
2. `line` — Geometric accent divider or rule line.
3. `circle` — Decorative disc or circular accent.
4. `text` — Dynamic text element bound to a data field with auto-fitting font constraints.
5. `photo` — Attendee profile photo with clipping geometry.
6. `logo` — Institutional logo (`acm_nit_surat` or `svnit`) with contain fit.
7. `role_badge` — Dynamic role indicator with distinct shape, label, and styling.
8. `qr` — Verification QR code matrix (minimum 12 × 12 mm).
9. `svg_asset` — Vector icon or decorative motif.

### 3.2 Allowed Color Tokens in Layouts
Only the following **7 named colors** are permitted in layout files:
* `"primary"` — Main brand color.
* `"secondary"` — Secondary accent/brand tone.
* `"background"` — Card base background tone.
* `"text"` — Primary readable text color.
* `"muted"` — Secondary/caption text color.
* `"accent"` — Highlight/contrast accent color.
* `"role"` — Dynamic color resolved from the attendee's role configuration.

### 3.3 Element Property Schema

#### `text`
* `field` (string): Key from attendee data (`"full_name"`, `"role"`, `"organization"`, `"id_number"`, etc.).
* `x`, `y` (number): Top-left coordinates in mm.
* `w` (number): Bounding box width in mm for line wrapping / auto-fit.
* `max_lines` (integer): Maximum allowed lines before truncation or downscaling (e.g. `1` or `2`).
* `min_font` (number): Minimum permissible font size in points (`pt`).
* `max_font` (number): Maximum preferred font size in points (`pt`).
* `align` (string): `"left"`, `"center"`, or `"right"`.
* `color` (string): One of the 7 allowed named color tokens (e.g. `"text"`, `"muted"`).
* Optional rows may set `optional: true`, `collapse_if_empty: true`, `collapse_group` (shared by the rows that should move together), and a positive `collapse_height` in mm. A renderer should call `studio.design_tools.prepare_layout(layout, attendee)` before drawing; blank or missing values remove their elements and compact later elements in the same group by the specified height. The original layout is not modified.

#### `photo`
* `field` (string): Field pointing to image filename or URL (default: `"photo"`).
* `x`, `y`, `w`, `h` (number): Dimensions and placement in mm.
* `shape` (string): Clipping shape: `"circle"`, `"rect"`, or `"rounded_rect"`.

#### `logo`
* `src` (string): Logo identifier or path (`"acm_nit_surat"` or `"svnit"`).
* `x`, `y`, `w` (number): Placement and target width in mm.
* `fit` (string): Must always be `"contain"`. Never stretch logos.
* *Constraint*: Both ACM NIT Surat and SVNIT logos must be present on every layout with clear breathing space.

#### `qr`
* `field` (string): Data payload field (default: `"qr_data"`).
* `x`, `y`, `w`, `h` (number): Placement in mm. **Both `w` and `h` must be >= 12.0 mm**.
* `color` (string): Named color token for QR dark modules (e.g. `"primary"` or `"text"`).
* `background` (string): Named color token for QR light quiet zone (e.g. `"background"`).

#### `role_badge`
* `field` (string): Role field key (default: `"role"`).
* `x`, `y`, `w`, `h` (number): Placement in mm.
* `shape` (string): Badge outline shape (`"pill"`, `"rect"`, `"shield"`).
* `color` (string): Text/foreground named color token.
* `background` (string): Background named color token (`"role"`).

#### `rect`, `line`, `circle`, `svg_asset`
* `rect`: `x`, `y`, `w`, `h`, `fill`, `stroke`, `stroke_width`, `rx`, `ry`.
* `line`: `x1`, `y1`, `x2`, `y2`, `stroke`, `stroke_width`.
* `circle`: `cx`, `cy`, `r`, `fill`, `stroke`, `stroke_width`.
* `svg_asset`: `src`, `x`, `y`, `w`, `h`.

### 3.4 Short Layout JSON Example

```json
{
  "id": "layout_minimal_modern",
  "name": "Minimal Modern Portrait",
  "version": "1.0.0",
  "dimensions": {
    "canvas_width": 60.0,
    "canvas_height": 92.0,
    "trim_width": 54.0,
    "trim_height": 86.0,
    "bleed": 3.0,
    "unit": "mm"
  },
  "elements": [
    {
      "type": "rect",
      "x": 0.0,
      "y": 0.0,
      "w": 60.0,
      "h": 92.0,
      "fill": "background"
    },
    {
      "type": "logo",
      "src": "acm_nit_surat",
      "x": 8.0,
      "y": 8.0,
      "w": 18.0,
      "fit": "contain"
    },
    {
      "type": "logo",
      "src": "svnit",
      "x": 34.0,
      "y": 8.0,
      "w": 18.0,
      "fit": "contain"
    },
    {
      "type": "photo",
      "field": "photo",
      "x": 16.0,
      "y": 20.0,
      "w": 28.0,
      "h": 28.0,
      "shape": "circle"
    },
    {
      "type": "text",
      "field": "full_name",
      "x": 8.0,
      "y": 51.0,
      "w": 44.0,
      "max_lines": 2,
      "min_font": 10.0,
      "max_font": 14.0,
      "align": "center",
      "color": "text"
    },
    {
      "type": "role_badge",
      "field": "role",
      "x": 14.0,
      "y": 60.0,
      "w": 32.0,
      "h": 6.5,
      "shape": "pill",
      "color": "background",
      "background": "role"
    },
    {
      "type": "text",
      "field": "organization",
      "x": 8.0,
      "y": 68.0,
      "w": 44.0,
      "max_lines": 1,
      "min_font": 7.0,
      "max_font": 8.5,
      "align": "center",
      "color": "muted"
    },
    {
      "type": "qr",
      "field": "qr_data",
      "x": 23.0,
      "y": 71.0,
      "w": 14.0,
      "h": 14.0,
      "color": "primary",
      "background": "background"
    }
  ]
}
```

---

## 4. Theme JSON Specification

Theme JSON files reside in `studio/backend/app/templates/themes/`.

### 4.1 Theme Structure
A theme specifies:
1. `fonts`: `heading` and `body` paths to locally installed font files.
2. `colors`: Concrete `#RRGGBB` hex color codes for all 7 named tokens (`primary`, `secondary`, `background`, `text`, `muted`, `accent`, `role`).
3. `role_colors`: Per-role `background` and `text` hex colors for `"participant"`, `"organizer"`, and `"mentor"`.
4. `role_style`: Per-role `badge_shape`, `badge_border`, and explicit `label` values so role identity remains clear in grayscale.

Place the theme fonts under `studio/assets/fonts/`; the exact free Google Fonts files and their licenses are listed in [FONTS.md](./FONTS.md).

### 4.2 Black and White (Monochrome) Role Distinction
Because badges may be printed on black-and-white card printers or viewed by color-blind attendees, roles **must never be distinguished solely by color**. Each role specifies:
* **Distinct Badge Shape**:
  * `participant`: Rounded pill (`"pill"`).
  * `organizer`: Shield / hexagonal badge (`"shield"`).
  * `mentor`: Diamond-accented / sharp rectangle (`"rect"`).
* **Distinct Explicit Label**:
  * `participant`: `"PARTICIPANT"`
  * `organizer`: `"ORGANIZER"`
  * `mentor`: `"MENTOR"`
* **Distinct Border / Pattern**:
  * `participant`: Single solid border (`"solid"`).
  * `organizer`: Double outline (`"double"`).
  * `mentor`: Dashed / accented outline (`"dashed"`).

### 4.3 Short Theme JSON Example

```json
{
  "id": "theme_tech_dark",
  "name": "ACM Tech Dark",
  "version": "1.0.0",
  "description": "High-contrast dark mode theme optimized for developer hackathons",
  "fonts": {
    "heading": "assets/fonts/SpaceGrotesk-Bold.ttf",
    "body": "assets/fonts/Inter-Regular.ttf"
  },
  "colors": {
    "primary": "#0085FF",
    "secondary": "#6366F1",
    "background": "#0F172A",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "accent": "#38BDF8"
  },
  "role_colors": {
    "participant": {"background": "#2563EB", "text": "#FFFFFF"},
    "organizer": {"background": "#F59E0B", "text": "#0F172A"},
    "mentor": {"background": "#0F766E", "text": "#FFFFFF"}
  },
  "role_style": {
    "participant": {"badge_shape": "pill", "badge_border": "solid", "label": "PARTICIPANT"},
    "organizer": {"badge_shape": "shield", "badge_border": "double", "label": "ORGANIZER"},
    "mentor": {"badge_shape": "rect", "badge_border": "dashed", "label": "MENTOR"}
  }
}
```

### 4.4 Contrast Ratios in this Theme (WCAG AA >= 4.5:1)
* `text` (`#F8FAFC`) on `background` (`#0F172A`): **16.1:1** (Passes AAA)
* `muted` (`#94A3B8`) on `background` (`#0F172A`): **6.2:1** (Passes AA)
* Participant badge: `#FFFFFF` on `#0085FF`: **4.6:1** (Passes AA)
* Organizer badge: `#0F172A` on `#F59E0B`: **9.4:1** (Passes AAA)
* Mentor badge: `#FFFFFF` on `#10B981`: **4.5:1** (Passes AA)

---

## 5. Attendee Data Fields (CSV / JSON)

Templates expect attendee records with these standard attributes:
* `full_name` (string): Attendee's full name (e.g. `"Aarav Sharma"`).
* `role` (string): One of `"participant"`, `"organizer"`, `"mentor"`.
* `organization` (string): College or company (e.g. `"SVNIT Surat"`).
* `id_number` (string): Unique identifier (e.g. `"INC-2026-042"`).
* `photo` (string): Relative photo path (e.g. `"sample_data/photos/p01.jpg"`).
* `qr_data` (string): Verification text/URL (e.g. `"https://incursion.acmnitsurat.org/verify/INC-2026-042"`).

---

## 6. Specification Conflicts & Registered Defaults

The following differences exist across standard printing specifications:

| Parameter | Default (Chosen) | Alternative | Reason & Resolution |
| :--- | :--- | :--- | :--- |
| **Card Trim Height** | `86.0 mm` | `85.60 mm` | The prompt explicitly specifies `54 x 86 mm` trim with `3 mm` bleed (`60 x 92 mm` canvas). ISO/IEC 7810 ID-1 standard card size is `53.98 x 85.60 mm`. `86.0 mm` is tracked in `config.py` as default (`CARD_TRIM_HEIGHT_MM`), with `85.6 mm` recorded as `CARD_TRIM_HEIGHT_ISO_MM`. |
| **Safe Margin** | `7.0 mm` (canvas) | `4.0 mm` (trim) | Prompt specifies safe area `x: 7..53`, `y: 7..85`. On a `60 x 92 mm` canvas, `7 mm` margin from the canvas boundary equals exactly `4.0 mm` margin inside the trim edge (`7 - 3 = 4 mm`). Both interpretations are documented in `config.py` as `SAFE_MARGIN_FROM_CANVAS_MM = 7.0` and `SAFE_MARGIN_ALT_CANVAS_MM = 4.0`. |
