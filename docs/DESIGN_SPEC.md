# Design Spec Specification (Team Contract v1.0)

This document is the shared team contract between **Person 1** (Backend & Data), **Person 2** (Rendering & Export), **Person 3** (Frontend), and **Person 4** (Card Design).

---

## 1. Purpose and Formulas

The core principle of ID Card Studio is: **Designs are data**.

Card generation proceeds in two deterministic stages:
```text
DesignSpec = Layout + Theme + BrandKit + EventInfo + PrintSettings
Final Card SVG = DesignSpec + Person Data
```
- **Same Spec + Same Person Data = 100% Identical Output** across all platforms and operating systems.
- Every model strictly forbids unexpected or unknown properties (`extra="forbid"`), preventing silent typos.

---

## 2. Units and Coordinate System

All spatial dimensions and layout values are specified in **millimeters (mm)**, with origin `(0, 0)` at the **top-left** of the canvas. Font sizes are specified in **points (pt)** (1 pt = 0.352778 mm).

| Region / Parameter | Dimension / Coordinates (mm) | Description |
| :--- | :--- | :--- |
| **Card Trim Size** | `54.0 × 86.0 mm` | Final cut size of the physical ID badge |
| **Bleed Margin** | `3.0 mm` (all 4 sides) | Extra background extension to prevent white borders after trimming |
| **Canvas Size** | `60.0 × 92.0 mm` | Full SVG coordinate box (`54 + 2*3` × `86 + 2*3`) |
| **Safe Margin** | `4.0 mm` inside trim | Inner padding from trim line |
| **Safe Area Box** | `x: 7.0..53.0 mm, y: 7.0..85.0 mm` | All critical text, barcodes, and logos must fit strictly inside this box |

---

## 3. Color Rules

1. **Layout JSON Files (`Layout`)**:
   - Layouts define visual geometry and typography hierarchy.
   - Layout elements **must NEVER use hex codes**. They only refer to theme color tokens:
     `"background"`, `"primary"`, `"secondary"`, `"accent"`, `"text"`, or `"none"`.
2. **Theme JSON Files (`Theme`)**:
   - Themes define concrete visual styles.
   - Theme palettes define hex codes (e.g., `"#1F6FEB"`), matching regex `^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$`.
3. **Brand Kit Overrides (`BrandKit`)**:
   - When `primary_color` or `secondary_color` are explicitly specified in a brand kit, they override the corresponding theme token in the merged `DesignSpec`.

---

## 4. Element Models Reference

Every element model includes an optional `id` string (regex `^[a-z0-9][a-z0-9_-]*$`). Within any layout or design spec, element IDs must be unique.

### 4.1 Rect (`rect`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"rect"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `x` | `float` | Required | Left position (mm) |
| `y` | `float` | Required | Top position (mm) |
| `w` | `float` | Required | Width (mm), `w > 0` |
| `h` | `float` | Required | Height (mm), `h > 0` |
| `fill` | `Fill` | `"none"` | Theme token or linear gradient |
| `stroke` | `LayoutColor` | `"none"` | Theme token or `"none"` |
| `stroke_width` | `float` | `0` | Stroke width (mm), `>= 0` |
| `radius` | `float` | `0` | Corner radius (mm), `>= 0` |
| `dash` | `Optional[list[float]]` | `None` | Stroke dash array |
| `opacity` | `float` | `1.0` | Opacity `0.0..1.0` |

### 4.2 Line (`line`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"line"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `x1` | `float` | Required | Start X position (mm) |
| `y1` | `float` | Required | Start Y position (mm) |
| `x2` | `float` | Required | End X position (mm) |
| `y2` | `float` | Required | End Y position (mm) |
| `stroke` | `LayoutColor` | Required | Theme token |
| `stroke_width` | `float` | `0.3` | Stroke width (mm), `> 0` |
| `dash` | `Optional[list[float]]` | `None` | Stroke dash array |
| `opacity` | `float` | `1.0` | Opacity `0.0..1.0` |

### 4.3 Circle (`circle`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"circle"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `cx` | `float` | Required | Center X coordinate (mm) |
| `cy` | `float` | Required | Center Y coordinate (mm) |
| `r` | `float` | Required | Radius (mm), `r > 0` |
| `fill` | `Fill` | `"none"` | Theme token or gradient |
| `stroke` | `LayoutColor` | `"none"` | Theme token or `"none"` |
| `stroke_width` | `float` | `0` | Stroke width (mm), `>= 0` |
| `opacity` | `float` | `1.0` | Opacity `0.0..1.0` |

### 4.4 Text (`text`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"text"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `field` | `Optional[str]` | `None` | Dynamic person field (e.g., `"name"`, `"department"`) |
| `value` | `Optional[str]` | `None` | Static literal text string |
| `x` | `float` | Required | Left position (mm) |
| `y` | `float` | Required | Baseline/top Y position (mm) |
| `w` | `float` | Required | Bounding box width (mm), `w > 0` |
| `font` | `"heading" \| "body"` | `"body"` | Theme font category |
| `color` | `LayoutColor` | `"text"` | Theme color token |
| `max_font` | `float` | `14.0` | Maximum font size in pt, `> 0` |
| `min_font` | `float` | `8.0` | Minimum font size in pt, `> 0`, `<= max_font` |
| `max_lines` | `int` | `1` | Max wrapping lines, `>= 1` |
| `align` | `"left" \| "center" \| "right"` | `"left"` | Text alignment |
| `bold` | `bool` | `False` | Bold typeface flag |
| `uppercase` | `bool` | `False` | Transform to uppercase flag |
*(Validation rule: Exactly one of `field` or `value` must be provided).*

### 4.5 Photo (`photo`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"photo"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `field` | `str` | `"photo"` | Source image filename field |
| `x` | `float` | Required | Left position (mm) |
| `y` | `float` | Required | Top position (mm) |
| `w` | `float` | Required | Photo box width (mm), `w > 0` |
| `h` | `float` | Required | Photo box height (mm), `h > 0` |
| `shape` | `"rect" \| "rounded" \| "circle"` | `"rect"` | Mask clipping shape |
| `radius` | `float` | `0` | Corner radius for `"rounded"`, `>= 0` |

### 4.6 Logo (`logo`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"logo"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `src` | `str` | Required | Brand kit logo key (`"acm_nitsurat"`, `"svnit"`) |
| `x` | `float` | Required | Left position (mm) |
| `y` | `float` | Required | Top position (mm) |
| `w` | `float` | Required | Target width (mm), `w > 0` |
| `h` | `Optional[float]` | `None` | Optional target height (mm); aspect ratio preserved if omitted |
| `fit` | `"contain"` | `"contain"` | Aspect ratio fit mode |

### 4.7 Role Badge (`role_badge`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"role_badge"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `field` | `str` | `"role"` | Dynamic person role field |
| `x` | `float` | Required | Left position (mm) |
| `y` | `float` | Required | Top position (mm) |
| `w` | `float` | Required | Badge width (mm), `w > 0` |
| `h` | `float` | Required | Badge height (mm), `h > 0` |
| `text_color` | `LayoutColor` | `"background"` | Contrast text token |

### 4.8 QR Code (`qr`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"qr"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `field` | `str` | `"qr_url"` | Target payload URL/text field |
| `x` | `float` | Required | Left position (mm) |
| `y` | `float` | Required | Top position (mm) |
| `w` | `float` | Required | Square width (mm), `w > 0` |
| `h` | `float` | Required | Square height (mm), `h == w` |
| `fg` | `LayoutColor` | `"text"` | Foreground QR token |
| `bg` | `LayoutColor` | `"background"` | Background QR token |
*(Validation rule: `w` and `h` must be strictly equal).*

### 4.9 SVG Asset (`svg_asset`)
| Field | Type | Default | Rule |
| :--- | :--- | :--- | :--- |
| `type` | `"svg_asset"` | Required | Fixed literal |
| `id` | `Optional[str]` | `None` | Unique element identifier |
| `src` | `str` | Required | Filename under `assets/art` |
| `x` | `float` | Required | Left position (mm) |
| `y` | `float` | Required | Top position (mm) |
| `w` | `float` | Required | Asset width (mm), `w > 0` |
| `h` | `float` | Required | Asset height (mm), `h > 0` |

---

## 5. Supporting Models

### 5.1 Theme
- `name`: `str` (slug)
- `colors`: `ThemeColors` (`background`, `primary`, `secondary`, `accent`, `text`)
- `fonts`: `ThemeFonts` (`heading`, `body`)
- `role_colors`: `dict[str, HexColor]` (must contain at least `participant`, `organizer`, `mentor`)

### 5.2 Person
- `name`: `str` (required, min length 1)
- `role`: `str` (default `"participant"`)
- `id`: `Optional[str]`
- `team`: `Optional[str]`
- `email`: `Optional[str]`
- `photo`: `Optional[str]`
- `qr_url`: `Optional[str]`
- `extra`: `dict[str, str]` (custom columns like `department`, `github`, etc.)
- Method: `get_field(name: str) -> Optional[str]` returns known attribute or `extra[name]`, or `None`.

### 5.3 EventInfo
- `event_name`: `Optional[str]`
- `tagline`: `Optional[str]`
- `venue`: `Optional[str]`
- `dates`: `Optional[str]`

### 5.4 BrandKit
- `logos`: `dict[str, str]` (keys `"acm_nitsurat"`, `"svnit"` with repo-relative paths)
- `primary_color`: `Optional[HexColor]`
- `secondary_color`: `Optional[HexColor]`
- `fonts`: `Optional[ThemeFonts]`

### 5.5 PrintSettings
- `dpi`: `int` (allowed values: `150`, `300`, `600`; default: `300`)
- `include_bleed`: `bool` (default: `True`)
- `crop_marks`: `bool` (default: `False`)
- `color_mode`: `"rgb" \| "grayscale"` (default: `"rgb"`)

### 5.6 PatchOp
- `op`: `"set" \| "add" \| "remove"`
- `path`: `str` (dotted path segment syntax)
- `value`: `Any` (required for `"set"` and `"add"`; forbidden for `"remove"`)

---

## 6. Patch Path Syntax and Examples

A patch path consists of dot-separated segments referencing object keys, list indices, or element IDs:

1. `elements.1.y`: Modify the Y coordinate of the second element in the `elements` list.
2. `elements.logo_left.w`: Modify the width of the element whose `id` is `"logo_left"`.
3. `theme.colors.primary`: Update the primary theme color to a new hex value.
4. `event.event_name`: Update the event title.
5. `print_settings.dpi`: Change output resolution to 600 DPI.
6. `elements`: Append a new element dictionary to the elements list (via `add` op).
7. `elements.badge_role`: Remove the badge element with `id="badge_role"` (via `remove` op).

*Note: Patching `schema_version` is strictly forbidden.*

---

## 7. Spec Examples

### 7.1 Valid Layout JSON (`classic.json`)
```json
{
  "name": "classic",
  "page": {
    "width_mm": 54,
    "height_mm": 86,
    "bleed_mm": 3,
    "safe_mm": 4
  },
  "elements": [
    {
      "type": "rect",
      "id": "card_bg",
      "x": 0,
      "y": 0,
      "w": 60,
      "h": 92,
      "fill": "background"
    },
    {
      "type": "logo",
      "id": "acm_logo",
      "src": "acm_nitsurat",
      "x": 8,
      "y": 8,
      "w": 18
    },
    {
      "type": "logo",
      "id": "svnit_logo",
      "src": "svnit",
      "x": 34,
      "y": 8,
      "w": 18
    },
    {
      "type": "text",
      "id": "participant_name",
      "field": "name",
      "x": 8,
      "y": 50,
      "w": 44,
      "font": "heading",
      "color": "text",
      "max_font": 14,
      "min_font": 9,
      "align": "center",
      "bold": true
    }
  ]
}
```

### 7.2 Valid Theme JSON (`clean_light.json`)
```json
{
  "name": "clean_light",
  "colors": {
    "background": "#FFFFFF",
    "primary": "#1F6FEB",
    "secondary": "#EAF1FD",
    "accent": "#38BDF8",
    "text": "#0B1220"
  },
  "fonts": {
    "heading": "Poppins",
    "body": "Inter"
  },
  "role_colors": {
    "participant": "#1F6FEB",
    "organizer": "#D9480F",
    "mentor": "#2F9E44"
  }
}
```

### 7.3 Valid Merged DesignSpec JSON
```json
{
  "schema_version": "1.0",
  "layout_name": "classic",
  "theme_name": "clean_light",
  "page": {
    "width_mm": 54,
    "height_mm": 86,
    "bleed_mm": 3,
    "safe_mm": 4
  },
  "theme": {
    "name": "clean_light",
    "colors": {
      "background": "#FFFFFF",
      "primary": "#1F6FEB",
      "secondary": "#EAF1FD",
      "accent": "#38BDF8",
      "text": "#0B1220"
    },
    "fonts": {
      "heading": "Poppins",
      "body": "Inter"
    },
    "role_colors": {
      "participant": "#1F6FEB",
      "organizer": "#D9480F",
      "mentor": "#2F9E44"
    }
  },
  "elements": [
    {
      "type": "rect",
      "id": "card_bg",
      "x": 0,
      "y": 0,
      "w": 60,
      "h": 92,
      "fill": "background"
    },
    {
      "type": "logo",
      "id": "acm_logo",
      "src": "acm_nitsurat",
      "x": 8,
      "y": 8,
      "w": 18
    },
    {
      "type": "logo",
      "id": "svnit_logo",
      "src": "svnit",
      "x": 34,
      "y": 8,
      "w": 18
    },
    {
      "type": "text",
      "id": "participant_name",
      "field": "name",
      "x": 8,
      "y": 50,
      "w": 44,
      "font": "heading",
      "color": "text",
      "max_font": 14,
      "min_font": 9,
      "align": "center",
      "bold": true
    }
  ],
  "brand": {
    "logos": {
      "acm_nitsurat": "assets/logos/acm_nitsurat.svg",
      "svnit": "assets/logos/svnit.svg"
    }
  },
  "event": {
    "event_name": "ACM Hackathon 2026",
    "venue": "SVNIT Campus",
    "dates": "Oct 10-12, 2026"
  },
  "print_settings": {
    "dpi": 300,
    "include_bleed": true,
    "crop_marks": false,
    "color_mode": "rgb"
  }
}
```

---

## 8. Freeze Policy

1. **Additive and Optional Only**: From this freeze forward, any schema modification must be strictly backward compatible. No existing field may be removed or renamed.
2. **Breaking Changes**: Any breaking change requires unanimous agreement from all 4 team members and must bump `SCHEMA_VERSION` (e.g. to `"2.0"`).
3. **Change Requests**: To request a new schema property, open a request with **Person 1**.

---

## 9. Not in the Spec on Purpose

The following are deliberately excluded from the `DesignSpec`:
- **Rendered Output**: Rendered SVG strings and raster PNG/PDF blobs are derived artifacts, never stored inside the spec.
- **Participant Photo Data**: Image binary data and base64 strings are kept external to keep specs lightweight, inspectable, and cacheable.
- **Raw AI Prompts / Logs**: AI is an assistant that outputs structured patches; internal prompts and raw outputs are not persisted in the spec.
