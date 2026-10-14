# Data formats and team integration contract

The renderer consumes a temporary Design Spec, a person, one layout JSON file, and one theme JSON file. The normalized models and all Design Spec field access live in `render/spec_adapter.py`; application code should use `export.api` rather than reading card fields itself.

## Temporary Design Spec

The file is one JSON object. The currently used fields and their rules are:

| Field | Type and requirement | Null or omitted behavior |
|---|---|---|
| `event` | Required object. | Missing or non-object is invalid. |
| `event.name` | String or `null`. | Null/empty renders visible `EVENT NAME` if used as text, and QA records a warning. |
| `event.tagline`, `event.venue`, `event.date` | String or `null`; optional event text fields. | A layout that uses a null/empty value renders a visible `<FIELD> NOT PROVIDED` fallback. The renderer warns. |
| `card` | Required object. | Missing or non-object is invalid. |
| `card.width_mm` | Positive number; trim width in mm. | Required; null is invalid. |
| `card.height_mm` | Positive number; trim height in mm. | Required; null is invalid. |
| `card.bleed_mm` | Non-negative number; bleed on each edge. | Required; null is invalid. |
| `card.safe_mm` | Non-negative number; safe inset within trim. | Required; null is invalid. |
| `layout` | Required non-empty string naming `templates/layouts/<layout>.json`. | Missing, empty, or null is invalid. |
| `theme` | Required non-empty string naming `templates/themes/<theme>.json`. | Missing, empty, or null is invalid. |
| `logos` | Optional array of strings; names correspond to files under `assets/`. | Omitted means `[]`; null or non-string entries are invalid. A layout logo not listed is omitted. A requested but missing file renders a placeholder. |
| `roles` | Present in the temporary example as an object keyed by role. | Currently ignored; role colors and the printed role label come from the theme and renderer. |
| `attendance_url_base` | Optional string or `null`. | Null/omitted skips the QR. Otherwise the renderer appends the person's ID to this prefix. |
| `dpi` | Optional positive integer. | Defaults to `300`; null, booleans, zero, and non-integers are invalid when read by QA. |

Unknown top-level or nested fields are not generally rejected. The `roles` object is retained only for the temporary schema and is not currently interpreted. Supported roles are `participant`, `organizer`, `mentor`, and `volunteer`.

Example (`specs/temp_spec.json`):

```json
{
  "event": {
    "name": null,
    "tagline": null,
    "venue": null,
    "date": null
  },
  "card": {
    "width_mm": 54,
    "height_mm": 86,
    "bleed_mm": 3,
    "safe_mm": 3
  },
  "layout": "classic",
  "theme": "blue",
  "logos": ["acm", "svnit"],
  "roles": {
    "participant": {},
    "organizer": {},
    "mentor": {},
    "volunteer": {}
  }
}
```

The resulting canvas is trim plus bleed on all sides: the example produces a 60 x 92 mm canvas around a 54 x 86 mm trim area.

## Layout files

Place a UTF-8 JSON object in `templates/layouts/<name>.json`; select it by the filename stem in the Design Spec. `name` and `_placeholder` may be included as descriptive metadata and are ignored by the renderer. `elements` is a required array. The renderer draws the background and trim fill before the elements in array order.

Each element uses:

| Property | Requirement / meaning |
|---|---|
| `id` | Optional string ID. Use unique IDs; QA and text clipping use them to identify elements. |
| `type` | Required: `rect`, `text`, `logo`, `photo`, `image`, or `qr`. |
| `position` | Required object with numeric `x` and `y` coordinates in mm. For text, `x` is the horizontal text anchor and `y` is the vertical center of the text box; the renderer computes the baseline. |
| `size` | Required object with positive numeric `width` and `height` in mm. |
| `color` | Required theme color name: `primary`, `secondary`, `background`, `text`, `text_on_primary`, or `accent`. Role-area rectangles use the role color but still need a valid `color` property. |
| `role_area` | Optional boolean. When true, the element is rendered in its role color and the root `role_area` settings draw the role label and cue. |
| `radius` | Optional numeric corner radius for rectangles; photo defaults to 12% of its smaller dimension. |

Element-specific properties:

- **`rect`**: `radius` is optional (defaults to `0`). `shape` is not used for rectangles.
- **`text`**: `data` is a `person.<field>` or `event.<field>` reference; `font_size`, `min_font_size`, `max_width`, and positive-integer `max_lines` are required. `weight` defaults to `"400"`; `alignment` is `start`, `middle`, or `end` and defaults to `start`. The theme's heading then body font families are searched in order. Text shrinks, wraps, and is shortened with an ellipsis only if needed.
- **`logo`**: `data` is a logo name; it is drawn only if that name appears in the spec's `logos` array. It is placed proportionally in the element's position/size slot.
- **`photo`**: `shape` is `circle` or `rounded_rect` and defaults to `circle`. `radius` applies to rounded rectangles. It uses the person's `photo` path; unavailable photos render initials. Keep the conventional element ID `person-photo`; the renderer and QA use that fixed ID.
- **`image`**: `data` is an asset filename under `assets/`. The asset is drawn proportionally; missing assets receive a visible placeholder. Only direct files within `assets/` are loaded.
- **`qr`**: `qr_size_mm` is a required positive size of at least 12 mm and must fit the element's width and height. Its payload is `attendance_url_base + person.id`; null URL or missing ID omits the QR.

Text `data` can refer to a string-valued event or person field. The standard fields are `event.name`, `event.tagline`, `event.venue`, `event.date`, `person.id`, `person.name`, and `person.role`.

The optional root `role_area` config is required if an element has `role_area: true`:

- `label.position` is numeric `{ "x": ..., "y": ... }`; `label.font_size` is positive and `label.alignment` defaults to `middle`.
- `cue.position` is numeric `{ "x": ..., "y": ... }`; `cue.size` contains positive `width` and `height`.
- The label and shape are selected from the person's role. The shape mapping is fixed: participant circle, organizer square, mentor triangle, volunteer diamond.

Full example (`templates/layouts/classic.json`):

```json
{
  "_placeholder": true,
  "name": "Classic",
  "role_area": {
    "label": {
      "position": { "x": 34, "y": 82 },
      "font_size": 3.2,
      "alignment": "middle"
    },
    "cue": {
      "position": { "x": 7, "y": 78.5 },
      "size": { "width": 5, "height": 5 }
    }
  },
  "elements": [
    {
      "id": "left-logo",
      "type": "logo",
      "data": "acm",
      "position": { "x": 6, "y": 6 },
      "size": { "width": 21, "height": 8 },
      "color": "accent"
    },
    {
      "id": "right-logo",
      "type": "logo",
      "data": "svnit",
      "position": { "x": 33, "y": 6 },
      "size": { "width": 21, "height": 8 },
      "color": "accent"
    },
    {
      "id": "event-band",
      "type": "rect",
      "position": { "x": 0, "y": 18 },
      "size": { "width": 60, "height": 13 },
      "color": "primary"
    },
    {
      "id": "event-name",
      "type": "text",
      "data": "event.name",
      "position": { "x": 30, "y": 26.5 },
      "size": { "width": 48, "height": 5 },
      "color": "text_on_primary",
      "font_size": 3.4,
      "min_font_size": 2.8,
      "max_lines": 1,
      "weight": "700",
      "alignment": "middle",
      "max_width": 48
    },
    {
      "id": "person-photo",
      "type": "photo",
      "position": { "x": 19, "y": 33 },
      "size": { "width": 22, "height": 22 },
      "color": "accent",
      "shape": "circle"
    },
    {
      "id": "person-name",
      "type": "text",
      "data": "person.name",
      "position": { "x": 30, "y": 66 },
      "size": { "width": 48, "height": 9 },
      "color": "text",
      "font_size": 5,
      "min_font_size": 3,
      "max_lines": 2,
      "weight": "700",
      "alignment": "middle",
      "max_width": 48
    },
    {
      "id": "attendance-qr",
      "type": "qr",
      "position": { "x": 44, "y": 38 },
      "size": { "width": 12, "height": 12 },
      "qr_size_mm": 12,
      "color": "text",
      "data": "attendance"
    },
    {
      "id": "role-band",
      "type": "rect",
      "position": { "x": 0, "y": 74 },
      "size": { "width": 60, "height": 18 },
      "color": "primary",
      "role_area": true
    }
  ]
}
```

## Theme files

Place a UTF-8 JSON object in `templates/themes/<name>.json`; select it by filename stem in the Design Spec.

| Property | Requirement / meaning |
|---|---|
| `name` | Optional descriptive label; ignored by rendering. |
| `_placeholder` | Optional metadata; ignored by rendering. |
| `colors` | Required object defining the six named colors below as distinct or reused six-digit hex strings. |
| `colors.primary` | Required `#RRGGBB`; main primary color. |
| `colors.secondary` | Required `#RRGGBB`; canvas/bleed background. |
| `colors.background` | Required `#RRGGBB`; trim-area background and QR background. |
| `colors.text` | Required `#RRGGBB`; standard body text. |
| `colors.text_on_primary` | Required `#RRGGBB`; text intended for primary backgrounds and initials contrast. |
| `colors.accent` | Required `#RRGGBB`; fallback and logo-slot accent. |
| `role_colors` | Required object with a unique six-digit hex color for each supported role: participant, organizer, mentor, volunteer. |
| `fonts.heading` | Required non-empty array of font-family strings, tried first. At least one family must resolve to an installed font. The current file lookup recognizes Arial, Segoe UI, and DejaVu Sans. |
| `fonts.body` | Optional array of font-family strings, appended as fallback candidates; defaults to `[]`. The current file lookup recognizes Arial, Segoe UI, and DejaVu Sans. |

All role colors must be valid and distinct. The renderer uses the same ordered font-family candidates for card text; the `heading` and `body` keys are both consumed.

Full example (`templates/themes/blue.json`):

```json
{
  "_placeholder": true,
  "name": "Blue",
  "colors": {
    "primary": "#2457A7",
    "secondary": "#DCE7F5",
    "background": "#FFFFFF",
    "text": "#172238",
    "text_on_primary": "#FFFFFF",
    "accent": "#CBD5E1"
  },
  "role_colors": {
    "participant": "#2457A7",
    "organizer": "#C2410C",
    "mentor": "#15803D",
    "volunteer": "#7E22CE"
  },
  "fonts": {
    "heading": ["Arial", "Segoe UI"],
    "body": ["Arial", "sans-serif"]
  }
}
```

## People CSV and JSON

The CSV loader requires `id`, `name`, `role`, and `photo` columns. CSV header whitespace is trimmed and column names are case-insensitive. Unknown columns are ignored. The values for `id`, `name`, `role`, and `photo` are trimmed; an empty value becomes null. A valid row requires a unique non-empty ID, a non-empty name, and one supported role. `photo` may be empty.

The JSON people file is an array of objects with the same lowercase keys. Each row's `id`, `name`, and `role` is validated as above. `photo` may be omitted, null, or empty. JSON keys are case-sensitive. People photos are paths relative to the input file's directory and must remain within that directory. Invalid rows are skipped and returned as `{ "row": number, "reason": string }`; CSV numbering counts the header as row 1, while JSON entries begin at row 1.

```json
[
  {
    "id": "person-001",
    "name": "Ada Lovelace",
    "role": "participant",
    "photo": "photos/ada.png"
  },
  {
    "id": "person-002",
    "name": "Grace Hopper",
    "role": "mentor",
    "photo": null
  }
]
```

The normalized `Person` model retains the source file so relative photo paths continue to resolve correctly. `export.api.load_people_file` returns `(people, problems)`.

## Export settings

`ExportSettings` accepts the following JSON-friendly dictionary:

| Key | Type / default | Valid values |
|---|---|---|
| `format` | string, `"svg"` | `"svg"`, `"pdf"`, `"png"` |
| `dpi` | positive integer, `300` | Positive integer; used for raster output and QA resolution checks. |
| `orientation` | string, `"portrait"` | `"portrait"` or `"landscape"` |
| `bleed` | boolean, `true` | `true` or `false`; false exports the trim-only card. |

Unknown keys and invalid values raise `ValueError`.

Print-sheet API calls use `PrintSheetSettings` instead:

| Key | Type / default | Valid values |
|---|---|---|
| `orientation` | string, `"portrait"` | `"portrait"` or `"landscape"` |
| `bleed` | boolean, `true` | Whether to include the card bleed canvas. |
| `crop_marks` | boolean, `true` | Include trim-corner crop marks. |
| `page_labels` | boolean, `true` | Include page number and the real event name when present. |
| `group_by_role` | boolean, `false` | Stable-sort cards by the fixed role order before placing them. |

Sheet paper size is a separate `"A4"` or `"A3"` argument.

## QA issue format

`qa.report.issues_to_dict` produces one JSON-friendly object per `Issue`:

```json
{
  "check": "text_overflow",
  "severity": "warning",
  "person_id": "person-001",
  "message": "Text in person-name was shortened with an ellipsis to fit."
}
```

`check` is the QA check name, `severity` is `"warning"` or `"error"`, `person_id` is a string or null, and `message` describes the result. A check execution failure is returned as an `"error"` issue; it does not stop the other QA checks.

## Add a layout or theme without code changes

1. Add a valid layout JSON file to `templates/layouts/` or theme JSON to `templates/themes/`.
2. Use the filename stem in the Design Spec's `layout` or `theme` field.
3. Run `python -c "from export.api import list_layouts, list_themes; print(list_layouts()); print(list_themes())"` and `pytest`.
4. Render sample cards with `python render_demo.py --layout <name> --theme <name>` to inspect the result.

## When Person 1's real Design Spec arrives

Keep application integrations calling `export.api`. Change only the normalization and field access in `render/spec_adapter.py` to map the real schema into `DesignSpec` and `Person`; the renderer, QA, exporters, layouts, themes, and public API should continue to use the normalized accessors. Update this document to reflect the agreed real input schema.
