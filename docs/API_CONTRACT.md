# API Contract Specification

This document specifies the HTTP endpoints available in ID Card Studio, serving as the interface contract for Person 3 (Frontend) and Person 2 (Rendering).

---

## 1. Endpoints Overview

| Method | Path | Owner | Status | Request Model | Response Model | Replaced in Task |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | P1 | **REAL** | None | `{"status": "ok"}` | - |
| `GET` | `/roles` | P1 | **REAL** | None | `list[dict]` | - |
| `GET` | `/schema/{name}` | P1 | **REAL** | None | `dict` (JSON Schema) | - |
| `GET` | `/templates/layouts` | P1 | **REAL** | None | `list[str]` | - |
| `GET` | `/templates/themes` | P1 | **REAL** | None | `list[str]` | - |
| `GET` | `/templates/layouts/{name}` | P1 | **REAL** | None | `Layout` | - |
| `GET` | `/templates/themes/{name}` | P1 | **REAL** | None | `Theme` | - |
| `POST` | `/spec/patch` | P1 | **REAL** | `PatchRequest` | `PatchResponse` | - |
| `POST` | `/brief` | P1 | **MOCK** | `BriefRequest` | `BriefResponse` | P1 Task 4/5 |
| `POST` | `/data/upload` | P1 | **MOCK** | Multipart (`file`) | `DataSummary` | P1 Task 3 |
| `POST` | `/drafts` | P1 | **MOCK** | `DraftsRequest` | `DraftsResponse` | P1 Task 6 |
| `POST` | `/render/preview` | P2 | **STUB (P2)** | `RenderPreviewRequest` | `RenderPreviewResponse` | Person 2 |

---

## 2. Standard Conventions and Error Format

### 2.1 The `mock` Flag
All mock responses carry `"mock": true` at top level so the frontend UI can visually signal when mock data is being served.

### 2.2 Error Handling: HTTP 422
When a request fails schema validation, loader checks (`SpecError`), or patch execution (`PatchError`), the API returns HTTP 422 with a structured error detail:
```json
{
  "detail": "op 1 (set elements.99.y): no element at index 99"
}
```

---

## 3. Endpoint Details & Examples

### 3.1 `GET /health`
- **Description**: Basic liveness probe.
- **Response Example**:
```json
{
  "status": "ok",
  "version": "0.0.1"
}
```

### 3.2 `GET /roles`
- **Description**: Returns all configured role badges from `templates/roles.json`.
- **Response Example**:
```json
[
  {
    "id": "participant",
    "label": "Participant",
    "description": "Standard event attendee"
  },
  {
    "id": "organizer",
    "label": "Organizer",
    "description": "Core organizing committee"
  },
  {
    "id": "mentor",
    "label": "Mentor",
    "description": "Judge or technical mentor"
  }
]
```

### 3.3 `GET /schema/{name}`
- **Description**: Returns JSON Schema for a model (`layout`, `theme`, `design-spec`, `brief`, `person`, `patch-op`).
- **Response Example (`GET /schema/person`)**:
```json
{
  "$defs": {},
  "properties": {
    "extra": {
      "default": {},
      "title": "Extra",
      "type": "object"
    },
    "name": {
      "minLength": 1,
      "title": "Name",
      "type": "string"
    },
    "role": {
      "default": "participant",
      "title": "Role",
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "title": "Person",
  "type": "object"
}
```

### 3.4 `GET /templates/layouts` and `GET /templates/themes`
- **Description**: Returns sorted names of all available starter templates.
- **Response Example (`GET /templates/layouts`)**:
```json
[
  "classic"
]
```

### 3.5 `GET /templates/layouts/{name}` and `GET /templates/themes/{name}`
- **Description**: Returns the validated JSON definition for a given template.
- **Response Example (`GET /templates/themes/clean_light`)**:
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

### 3.6 `POST /spec/patch`
- **Description**: Applies a list of atomic `PatchOp` operations to an existing `DesignSpec`.
- **Request Example**:
```json
{
  "spec": { ... },
  "ops": [
    {
      "op": "set",
      "path": "theme.colors.primary",
      "value": "#D9480F"
    }
  ]
}
```
- **Response Example**:
```json
{
  "spec": { ... }
}
```

### 3.7 `POST /brief` (MOCK)
- **Description**: Parses plain text to extract event parameters and missing fields.
- **Request Example**:
```json
{
  "text": "Design badges for SVNIT ACM Hackathon 2026 on Oct 10."
}
```
- **Response Example**:
```json
{
  "brief": {
    "design_type": "id_card",
    "event_name": null,
    "tagline": null,
    "dates": null,
    "venue": null,
    "roles": null,
    "counts": null,
    "fields_to_show": null,
    "card_size": null,
    "orientation": null,
    "style_hint": null,
    "lanyard_hole": null
  },
  "missing": [
    "event_name",
    "tagline",
    "dates",
    "venue",
    "roles",
    "fields_to_show"
  ],
  "questions": [
    {
      "field": "event_name",
      "text": "What is the official name of the event?",
      "kind": "text",
      "options": null,
      "default": null,
      "skippable": false
    }
  ],
  "mock": true
}
```

### 3.8 `POST /data/upload` (MOCK)
- **Description**: Ingests participant CSV file via multipart upload.
- **Request**: Multipart form field `file=@attendees.csv`.
- **Response Example**:
```json
{
  "people_loaded": 42,
  "column_mapping": {
    "name": "name",
    "role": "role",
    "team": "team",
    "email": "email",
    "id": "id"
  },
  "issues": {
    "missing_names": 0,
    "invalid_roles": 0,
    "duplicate_ids": 0
  },
  "warnings": [],
  "mock": true
}
```

### 3.9 `POST /drafts` (MOCK)
- **Description**: Returns candidate design specs for the organizer to pick from.
- **Request Example**:
```json
{
  "brief": { "design_type": "id_card" },
  "event": { "event_name": "ACM Hackathon 2026" },
  "count": 3
}
```
- **Response Example**:
```json
{
  "drafts": [
    { "schema_version": "1.0", "theme": { "colors": { "primary": "#1F6FEB" } } },
    { "schema_version": "1.0", "theme": { "colors": { "primary": "#D9480F" } } },
    { "schema_version": "1.0", "theme": { "colors": { "primary": "#2F9E44" } } }
  ],
  "mock": true
}
```

### 3.10 `POST /render/preview` (STUB - Owned by Person 2)
- **Description**: Renders a card preview SVG for a specific person.
- **Owner**: Person 2 (`api/routes_render.py`). Person 2 documents their full render API in `docs/p2/`.
