# Person 1 (Backend: AI, Data, and Spec) Tasks

Track progress for Person 1 implementation tasks.

- [x] **Task 1: FastAPI setup, router auto-discovery, and routes contract**
  - Modular routers auto-discovered under `app/api/routes_*.py`
  - CORS enabled for frontend
  - Real `/health`, `/roles`, `/schema/{name}`, `/templates/layouts`, `/templates/themes`, and `/spec/patch`
  - Standardized error handlers for `SpecError` and `PatchError` (HTTP 422)
  - Mock endpoints for `/brief`, `/data/upload`, and `/drafts`

- [x] **Task 2: Design Spec freeze, PrintSettings, custom fields, PatchOp, and validation**
  - `SCHEMA_VERSION = "1.0"` in `constants.py` and `DesignSpec`
  - Unique `id` validator for all layout elements
  - `PrintSettings` (dpi, bleed, crop_marks, color_mode)
  - `Person.extra` and `Person.get_field(name)`
  - Dotted path `PatchOp` ("set", "add", "remove") and pure `apply_patch` engine
  - Deep-copy merging in `merge_design_spec()` with brand override and logo validation

- [x] **Task 3: CSV loader, column mapping, and validation**
  - Robust CSV ingestion, auto-detection of delimiters, column aliasing
  - Issue detection (missing fields, format errors, unreadable photos)
  - Clean `Person` record generation

- [x] **Task 4: AI brief extraction (strict JSON, retry)**
  - Structured prompt to Gemini with system instructions
  - JSON schema enforcement and validation retry logic

- [x] **Task 5: Missing-info logic and follow-up questions**
  - Identification of required vs optional event info
  - Dynamic interactive follow-up questions for organizers

- [x] **Task 6: Draft generator (layout x theme = 3 specs)**
  - Cartesian product matching layouts and themes with event brief
  - Color palette selection and layout fit scoring

- [ ] **Task 7: SQLite storage and version history**
  - Local database storage for projects, drafts, and edit history
  - Version snapshots and restore capabilities

- [ ] **Task 8: AI refinement patches (stretch)**
  - Natural language instruction to `PatchOp` translation
  - Iterative prompt refinement and diff preview
