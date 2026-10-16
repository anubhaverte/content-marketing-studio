# ID Card Studio: Durable Master Roadmap & Project Continuity Guide

**Document Purpose:** Master project continuity reference for ID Card Studio (Track 4, ACM NIT Surat Hackathon). This document preserves every product requirement, feature status, phase boundary, ownership rule, architectural decision, and verified test outcome across Antigravity and AI pair-programming sessions.

---

## 1. Product Objective and Complete User Workflow

ID Card Studio is an automated, data-driven ID card generation and print-production studio. It transforms raw attendee data and brief constraints into sharp, print-ready vector cards meeting professional graphic design and print manufacturing specifications.

### Complete End-to-End User Journey

```
[Organizer Input]
       │
       ▼
1. Data Ingestion: Upload CSV (messy data with errors, accents, missing fields)
       │
       ▼
2. Ingestion Validation: Schema checks, column mapping, issue summary (names, roles, IDs)
       │
       ▼
3. Brief Intake & AI Extraction: Natural language event prompt parsed into Brief fields
       │
       ▼
4. Follow-up Clarification: Interactive questions for missing event parameters (dates, venue)
       │
       ▼
5. Design Draft Generation: Deterministic scoring & ranking of layout + theme combinations
       │
       ▼
6. Attendee Photo Processing: OpenCV face detection, face-aware crop, blur score, resolution
       │
       ▼
7. Spec Customization: Interactive preview, layout/theme selection, spec patch operations
       │
       ▼
8. Card Rendering: Code-built SVG (54×86mm trim, 3mm bleed, 4mm safe, embedded fonts, logos)
       │
       ▼
9. Automated Quality Assurance: Checks for contrast, overflow, overlap, logo ratio, resolution
       │
       ▼
10. Export & Production: Individual vector SVG/PDF/PNG, collated multi-page PDF, or batch ZIP
       │
       ▼
11. Frontend Application: Next.js UI guiding the organizer through the full pipeline
       │
       ▼
12. Shareable Demo & Production Deployment: Verifiable build, zero surprises, real printout
```

---

## 2. Mandatory Feature Inventory

Status Categories:
- `[x] VERIFIED COMPLETE`: Implemented, tested, and independently verified with passing tests.
- `[ ] IN PROGRESS / PARTIAL`: Partially implemented or awaiting full multi-component integration.
- `[ ] BLOCKED`: Cannot proceed without external teammate handoff or missing prerequisite.
- `[ ] NOT STARTED`: Planned for subsequent phases.

### A. Data Ingestion & Validation
- [x] **CSV Upload & Parsing:** Multipart file upload endpoint `POST /data/upload` accepting participant data. (Verified: `test_api_contract.py`)
- [x] **Encoding & Dialect Handling:** Robust parsing supporting UTF-8, CRLF/LF line endings, and quoted fields. (Verified: `test_csv_loader.py`)
- [x] **Column Normalization & Mapping:** Automatic mapping of CSV columns (Name, Role, Team, Photo, ID, Email, QR URL). (Verified: `test_csv_loader.py`)
- [x] **Messy Data Validation:** Identification of missing names, unknown roles, duplicate IDs, missing photos, very long names (40–50 chars), single-word names, accented glyphs, and bad whitespace. (Verified: 23 passing tests in `test_csv_loader.py`, exact 12-metric ground truth match on 250-row `people_messy.csv`)
- [x] **Validation Summary & Issue Reporting:** Accurate count reporting of `people_loaded`, `column_mapping`, `issues`, and `warnings`.

### B. AI Brief Extraction & Clarification
- [x] **Brief Schema & Extraction:** `POST /brief` extracting `design_type`, `event_name`, `tagline`, `dates`, `venue`, `roles`, `card_size`, `orientation`, `style_hint`. (Verified: `test_brief_extract.py`)
- [x] **Missing Information Detection:** Deterministic detection of unspecified event parameters. (Verified: `test_brief_extract.py`)
- [x] **Follow-up Clarifying Questions:** Dynamic generation of typed follow-up questions (`text`, `choice`, `number`, `boolean`). (Verified: `test_brief_extract.py`)
- [x] **Deterministic Offline Fallback:** Regex- and heuristic-based extraction when AI is unconfigured or unreachable. (Verified: 14 passing tests in `test_brief_extract.py`)
- [ ] **Live Gemini Connectivity:** Direct API calls using `GEMINI_API_KEY` via Google GenAI SDK. *(Status: NOT VERIFIED. Offline fallback is verified; live API key has not been configured in the test environment.)*

### C. Design Generation & Draft Selection
- [x] **Deterministic Candidate Generation:** `POST /drafts` generating scored and ranked `DesignSpec` candidates. (Verified: `test_drafts.py`)
- [x] **Brief Style Hint Scoring:** Deterministic scoring of layout and theme compatibility matching brief hints (clean, tech, bold). (Verified: `test_drafts.py`)
- [x] **Diversity Algorithm:** Multi-pass candidate selection prioritizing unused layouts and themes. (Verified: `test_drafts.py`)
- [x] **Deterministic Fallback Variations:** Color variation generation marked `is_mock=True` when catalog is smaller than requested draft count. (Verified: `test_drafts.py`)
- [ ] **Dynamic Multi-Catalog Discovery (3 × 3):** Full discovery over 3 distinct layouts × 3 distinct themes. *(Status: BLOCKED in Phase 4A pending P4 delivery of missing catalogs.)*
- [ ] **Three Distinct Passing Drafts:** 3 distinct drafts that simultaneously pass all QA rules without relying on fallback mocks. *(Status: BLOCKED in Phase 4A.)*

### D. Attendee Photo Processing (CRITICAL MODULE)
*File Location:* [`backend/app/assets/photo_utils.py`](file:///c:/Users/ANUBHAV/Downloads/workspace-01a11561-eca6-7528-8b22-be365d148db8/backend/app/assets/photo_utils.py)  
*Designated Owner:* **Person 2** (`docs/OWNERS.json`)  
*Current Verified State:* ✅ **COMPLETE & VERIFIED** (14 focused tests in `backend/tests/p2/test_photo_utils.py` pass; full repo suite 201 pass).

- [x] **OpenCV Face Detection (`detect_faces`):** Computer vision face detection using OpenCV YCrCb + HSV skin-color segmentation and morphological contour analysis. (Verified: `test_photo_utils.py:test_detect_faces_centered`)
- [x] **Face-Aware Centered Crop (`face_crop`):** Dynamic crop centered on the face box adjusted to the card frame aspect ratio without stretching or squashing. (Verified: `test_photo_utils.py:test_face_crop_centered`)
- [x] **Off-Center & Multi-Face Handling:** Proper centering on prominent face; intelligent bounding box selection for multiple faces; frame shift tracking off-center faces. (Verified: `test_photo_utils.py:test_detect_faces_multiple`, `test_face_crop_off_center_shifts_frame`)
- [x] **No-Face Fallback:** Deterministic centered fallback crop when no face is detected; initials fallback when no image exists or image is corrupt. (Verified: `test_photo_utils.py:test_face_crop_no_face_fallback`, `test_face_crop_corrupt_and_missing_raise`)
- [x] **Blur Assessment (`blur_score`):** Variance of the Laplacian calculation flagging blurry images below threshold (< 100.0). (Verified: `test_photo_utils.py:test_blur_score_sharp_vs_blurry`)
- [x] **Print Resolution Check (`check_resolution`):** Calculation verifying whether physical image dimensions satisfy 300 DPI at specified frame width and height in mm. (Verified: `test_photo_utils.py:test_check_resolution`)
- [x] **Pipeline Integration:** Integrated into SVG card rendering via `render/photo.py:photo_markup()`, emitting actionable QA warnings and embedding face-cropped image bytes. (Verified: `test_photo_utils.py:test_photo_markup_integration`, `test_export.py`)

### E. Card Rendering & Geometry
- [x] **Code-Built SVG Architecture:** Strict adherence to code-assembled SVG without bitmap generator hallucinations. (Verified: `render/renderer.py`, `test_hello_card.py`)
- [x] **Standard Physical Geometry:** Everything in millimeters. Canvas 60×92 mm, Trim 54×86 mm (3mm bleed), Safe Margin 4mm (inset 7..53mm, 7..85mm). (Verified: `test_export.py:test_trim_and_landscape_viewport`)
- [x] **Role Color & Accessibility Differentiation:** Distinct colors per role (`participant`, `organizer`, `mentor`, `volunteer`) with mandatory shape cues (circle, square, triangle, diamond) ensuring readability in black-and-white. (Verified: `render/renderer.py`)
- [x] **Dual Mandatory Logos:** ACM NIT Surat and SVNIT logos present on every card, never stretched (proportional scaling). (Verified: `render/renderer.py`)
- [x] **Text Fitting & Typography:** Auto-fitting font sizing and multi-line wrapping with bounded safe-area clipping. (Verified: `test_qa.py:test_accented_and_tall_glyphs_stay_inside_name_box`)
- [x] **Missing Photo Initials Fallback:** High-contrast circular initials badge automatically drawn when attendee photo is omitted. (Verified: `test_qa.py:test_missing_photo_initials_have_theme_contrast_for_every_role_and_design`)
- [x] **Dynamic QR Code Generation:** QR check-in codes generated and embedded when `attendance_url_base` or `qr_url` is present. (Verified: `render/qr.py`)

### F. Quality Assurance (QA) Engine
- [x] **Independent Rule Checks (`qa/checks.py`):**
  - `text_overflow`: Detects text exceeding safe area or designated element bounding box.
  - `logo_aspect_ratio`: Detects distorted or stretched logos.
  - `contrast`: Validates WCAG AA 4.5:1 contrast between text and background/role fills.
  - `overlap`: Flags unintended intersections between non-paired layout elements.
  - `empty_fields`: Flags missing required fields and placeholder usage.
  - `data_match`: Verifies rendered SVG text matches input attendee record.
  - `resolution`: Flags exported PNG images rendered below 300 DPI target resolution.
- [x] **Isolated QA Execution:** Exceptions in any single check do not abort other QA checks. (Verified: `test_qa.py:test_exception_in_one_check_does_not_stop_other_checks`)
- [x] **Structured Reporting:** Issues formatted into JSON-serializable dictionaries with severity, check ID, person ID, and message. (Verified: `test_qa.py:test_issue_reporting_is_readable_and_json_friendly`)

### G. Production Export & Delivery
- [x] **Vector SVG Export:** Full standalone SVG output with embedded fonts and styles. (Verified: `test_export.py`)
- [x] **Vector PDF Export:** CairoSVG vector PDF output embedding fonts without rasterization. (Verified: `test_export.py`)
- [x] **High-DPI PNG Export:** Pixel-exact raster PNG generation at 150, 300, and 600 DPI. (Verified: `test_export.py`)
- [x] **Batch ZIP Archive Packaging:** Packaging individual attendee card exports with Windows-safe sanitization and comprehensive `report.json`. (Verified: `test_export.py`, `test_render_batch.py`)
- [x] **Collated Multi-Page PDF:** Assembling all attendee cards into a single multi-page PDF document via `pypdf.PdfWriter`. (Verified: `test_export.py`, `test_render_batch.py`)
- [x] **Bounded Batch Processing:** Enforced non-empty attendee lists and 500-attendee batch limits preventing resource exhaustion. (Verified: `test_render_batch.py`)
- [x] **Partial Failure Resilience:** Graceful handling of individual attendee rendering failures in batch ZIP mode, documenting failure causes in `report.json` while exporting all successful cards. (Verified: `test_render_batch.py`)

### H. Template Catalogs & Assets
- [ ] **3 Layouts × 3 Themes Catalog:** Complete set of 3 distinct layouts and 3 distinct themes across catalogs. *(Status: BLOCKED in Phase 4A. Backend catalog contains 1 layout / 1 theme; root renderer contains 2 layouts / 2 themes.)*
- [ ] **Final Vector Logo Assets:** Production vector SVGs for ACM NIT Surat and SVNIT in `assets/`. *(Status: Placeholders active with intentional warnings; P4 owned.)*

### I. Frontend User Interface
- [ ] **Next.js Single-Page / Multi-Step UI (`frontend/`):** Guided workflow from CSV upload to batch export. *(Status: NOT STARTED; scheduled for Phase 6 under P3 ownership.)*
- [ ] **Live Interactive Preview Canvas:** In-browser live SVG card preview rendering via `POST /render/preview`.
- [ ] **Interactive Patch & Customization:** Direct visual styling controls wired to `POST /spec/patch`.

### J. Deployment & Release Proof
- [ ] **End-to-End Verified Run:** Complete execution from messy CSV upload to physical print export.
- [ ] **Rehearsed Demo Execution:** Verified zero-surprise demonstration script.

---

## 3. Phase-by-Phase Execution Plan

*Based directly on [`docs/PHASES.md`](file:///c:/Users/ANUBHAV/Downloads/workspace-01a11561-eca6-7528-8b22-be365d148db8/docs/PHASES.md).*

### Phase 0: Setup and Toolchain Proof
- **Objective:** Folder structure, project memory, Pydantic schemas, CairoSVG vector proof, 250-row messy sample data, check_env.
- **Owner:** Person 1 & Person 2
- **Status:** **COMPLETE**
- **Verified Evidence:** 23 passing tests in `backend/tests/test_env.py`, 166 passing tests on initial integration merge.
- **Exit Condition Met:** CairoSVG compiles to vector PDF/PNG; `check_env.py` passes cleanly.

### Phase 1: Single Card
- **Objective:** One hardcoded SVG card, both real logos, fonts embedded, filled from Python dict, PDF and PNG export.
- **Owner:** Person 2
- **Status:** **COMPLETE**
- **Verified Evidence:** `scripts/hello_card.py` renders 60×92mm canvas, CairoSVG outputs confirmed in `output/hello_card.pdf` and `output/hello_card.png`.
- **Exit Condition Met:** Sharp, print-ready card file produced at physical dimensions.

### Phase 2: Design Spec
- **Objective:** Layout + Theme + Brand Kit + Event merging via `DesignSpec`. Renderer for all element types, role colors, text auto-fit, photo clipping. `preview.py` renders preview image.
- **Owner:** Person 1 (Spec/Merge) & Person 2 (Renderer/Preview)
- **Status:** **COMPLETE**
- **Verified Evidence:** `backend/tests/p1/test_merge.py`, `backend/tests/p1/test_patch.py`, `backend/tests/p2/test_render_preview.py` passing (8 tests). `POST /render/preview` returns live SVG.
- **Exit Condition Met:** Changing spec values modifies card output without manual code alterations.

### Phase 3: Data
- **Objective:** CSV loader and column mapping, validation against `expected_issues.json`, batch render, QR codes, face-centered photo crops.
- **Owner:** Person 1 (CSV / Validation) & Person 2 (Batch Render / QR / Photo)
- **Status:** **COMPLETE** (CSV validation, batch multi-format export, and OpenCV face-aware photo processing fully implemented and verified).
- **Verified Evidence:**
  - `backend/tests/p1/test_csv_loader.py`: 23 passed, exact match against 12 validation categories in `sample_data/expected_issues.json`.
  - `backend/tests/p2/test_render_batch.py`: 13 passed, verifying ZIP packaging, collated multi-page PDF, JSON reporting, and partial failures.
  - `backend/tests/p2/test_photo_utils.py`: 14 passed, verifying OpenCV face detection, face-aware crop, Laplacian blur score, DPI resolution checks, and rendering pipeline integration.
  - `export/batch.py` & `export/exporters.py`: Verified multi-format export.
- **Outstanding Tasks:** None.
- **Exit Condition for Phase 3 Met:** 200+ cards generated correctly from CSV with face-centered photo crops and QR check-in codes.

### Phase 4: Drafts
- **Objective:** 3 layouts × 3 themes, deterministic draft generator, QA validators (overflow, logo ratio, contrast, overlap, empty fields, data match, resolution).
- **Owner:** Person 1 (Generator), Person 2 (QA Validators), Person 4 (Layouts & Themes Catalog)
- **Status:** **BLOCKED at Phase 4A**
- **Verified Evidence:**
  - `backend/tests/p1/test_drafts.py`: 9 passed, deterministic draft generation algorithm verified.
  - `tests/test_qa.py`: 15 passed, QA rule suite verified across available combinations.
- **Blocker:**
  - Catalog expansion (Phase 4A): Catalog lacks the 3 layouts × 3 themes required by `docs/PHASES.md`. Backend catalog has 1 layout × 1 theme; root catalog has 2 layouts × 2 themes.
- **Exit Condition for Phase 4:** 3 clearly distinct candidate drafts generated from brief, all passing QA with zero fatal errors.

### Phase 5: Brief and Questions
- **Objective:** Gemini extraction into Brief (with fallback if AI fails), missing-info logic, and follow-up questions.
- **Owner:** Person 1
- **Status:** **COMPLETE (Offline) / PARTIAL (Live API)**
- **Verified Evidence:** `backend/tests/p1/test_brief_extract.py`: 14 passed. Complete brief extracts event details; incomplete brief identifies missing parameters and formulates questions.
- **Outstanding:** Optional live API validation when `GEMINI_API_KEY` is provided.
- **Exit Condition Met:** Input sentence produces structured brief and clarifying questions.

### Phase 6: Frontend and Export
- **Objective:** Next.js application with screens: Describe, Questions, Data check, Drafts, Editor, Export. Export settings, print sheets with crop marks and bleed.
- **Owner:** Person 3 (Frontend)
- **Status:** **NOT STARTED**
- **Dependencies:** Stable backend endpoints (`/brief`, `/data/upload`, `/drafts`, `/spec/patch`, `/render/preview`, `/render/batch`).
- **Exit Condition:** Complete card generation workflow executable directly from web browser.

### Phase 7: Stretch Features
- **Objective:** Editable drafts, saved templates, natural language refinement via patch operations, version history, lanyard mockup preview, certificate generation.
- **Owner:** Collaborative (P1/P2/P3/P4)
- **Status:** **NOT STARTED**

### Phase 8: Polish & Rehearsal
- **Objective:** Comprehensive integration test, updated documentation, rehearsed demo without surprises, real physical printout verification.
- **Owner:** All Team Members
- **Status:** **NOT STARTED**
- **Exit Condition:** Clean demonstration run and successful physical print.

---

## 4. Phase 4A Blocker Analysis & Ownership Handoff

### Exact Catalog Inventory

| Catalog Location | Layouts Present | Themes Present | Combinations | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Catalog** (`backend/app/templates/`) | `classic.json` (1) | `clean_light.json` (1) | 1 × 1 = 1 | **Missing 2 layouts, 2 themes** |
| **Root Renderer Catalog** (`templates/`) | `classic.json`, `split.json` (2) | `blue.json`, `dark.json` (2) | 2 × 2 = 4 | **Missing 1 layout, 1 theme** |
| **Phase 4 Target Requirement** | 3 layouts | 3 themes | 3 × 3 = 9 | **UNMET** |

### Verification Findings
1. All 4 combinations in the root renderer catalog (`classic+blue`, `classic+dark`, `split+blue`, `split+dark`) were rendered and validated through `qa/checks.py:run_qa`. No crashes occurred, and expected placeholder warnings for missing logos were emitted.
2. `POST /drafts` currently returns only 1 true draft from the backend catalog, requiring synthetic primary-color variations marked `is_mock=True` to satisfy `count=3`.
3. Generating 3 genuinely distinct drafts from the catalog requires Person 4 to supply the missing template definitions.

### Ownership Boundary
- **Owner:** **Person 4** owns `backend/app/templates/layouts/`, `backend/app/templates/themes/`, `templates/`, and `assets/` per [`docs/OWNERS.json`](file:///c:/Users/ANUBHAV/Downloads/workspace-01a11561-eca6-7528-8b22-be365d148db8/docs/OWNERS.json).
- **Rule Enforcement:** Under Rule 10 ("Edit only files owned by the person you are helping") and `docs/TEAM.md`, assistants must not fabricate mock layouts or themes in Person 4's directories.

---

## 5. Verification Status vs. Assumptions

### Category 1: Independently Verified Complete
- CSV Upload, Schema Parsing, and 12-category Ground-Truth Validation (`backend/tests/p1/test_csv_loader.py` — 23 tests).
- Brief Extraction, Missing Info Logic, Question Formulation, Offline Fallback (`backend/tests/p1/test_brief_extract.py` — 14 tests).
- Deterministic Draft Generator Scoring and Diversity (`backend/tests/p1/test_drafts.py` — 9 tests).
- Specification Merging and Atomic Patching (`backend/tests/p1/test_merge.py`, `test_patch.py` — 19 tests).
- SVG Card Renderer & Geometry Engine (`render/renderer.py`, `tests/test_hello_card.py`).
- Automatic QA Checks (`tests/test_qa.py` — 15 tests).
- Vector PDF, High-DPI PNG, and SVG Exporters (`tests/test_export.py` — 16 tests).
- Live SVG Preview Route `POST /render/preview` (`backend/tests/p2/test_render_preview.py` — 8 tests).
- Batch Render Route `POST /render/batch` with ZIP packaging and collated PDF (`backend/tests/p2/test_render_batch.py` — 13 tests).
- Attendee Photo Processing with OpenCV face detection, face crop, blur scoring, and DPI checks (`backend/tests/p2/test_photo_utils.py` — 14 tests).
- Phase 6 Frontend Application: Next.js App Router, Tailwind CSS, 5-screen Card Studio wizard, backend API client, and live dev server (`frontend/`, `docs/p3/`).
- Total Test Baseline: **201 passed, 0 failed, 103 warnings** across full repository.

### Category 2: Reported Complete / Unverified Under Real Conditions
- **Live Gemini Extraction:** Offline heuristics pass 100%; live calls to Google Gemini API unverified due to absent credentials.
- **Physical Print Dimensions:** CairoSVG millimeter outputs verified mathematically and via PDF bounding boxes; physical paper printout not yet executed.

### Category 3: In Progress / Partially Implemented
*(All started backend core phases and Phase 6 frontend are complete; Phase 4A is blocked on external catalog input).*

### Category 4: Blocked or Not Started
- **Phase 4A Catalog Expansion:** Blocked on Person 4 delivering the 3 layouts × 3 themes catalog.
- **Phase 7 & 8:** Stretch features, final rehearsals, and demo packaging not started.

---

## 6. Next Action and Execution Continuity Rules

### Immediate Next Action
**Coordinate with Person 4** to author and deliver the missing layout and theme definitions:
1. Deliver 2 additional layouts and 2 additional themes to `backend/app/templates/` (canonical P1 `Layout` and `Theme` schemas).
2. Deliver 1 additional layout and 1 additional theme to root `templates/` (renderer format), ensuring both catalogs support at least 3 layouts × 3 themes.
3. Deliver vector logos (`assets/acm.svg` and `assets/svnit.svg`) to resolve placeholder asset warnings.

### Execution Continuity Protocols for Future Sessions
1. **Always Read Both Status Files First:** At the start of every session or task, read `docs/MASTER_ROADMAP.md` and `EXECUTION_STATUS.md`, and inspect `git status --short`.
2. **Preserve Historical Evidence:** Never overwrite or delete prior phase test records or findings in `EXECUTION_STATUS.md`. Append new phase verification results sequentially.
3. **Strict Ownership Adherence:** Check `docs/OWNERS.json` before touching any file. If a task requires modifying a file owned by another teammate, stop and document the boundary.
4. **Self-Contained Prompts:** Execute each major phase with a single comprehensive prompt rather than multiple fragmented micro-tasks.
5. **Pre-Push Validation:** Always run the complete test suite (`pytest`) and ownership validator (`python scripts/check_ownership.py --owner <pN>`) before reporting completion.
