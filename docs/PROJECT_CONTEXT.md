# Track 4: Content and Marketing Studio (ACM NIT Surat Hackathon)

> Source of truth for the whole project. Read this at the start of every session and before every phase.

## 1. What we are building
A design tool that turns a plain-English request into print-ready ID cards. Example request: "ID cards for our 24-hour hackathon on 18 October at SVNIT, with separate looks for participants, organizers and mentors."
The tool asks for whatever is missing (event name, venue, fields to show), builds 2-3 different card designs, lets the user pick and tweak one, and exports high-quality files (PDF, PNG, SVG) ready for the printer.
KEY IDEA: this is NOT an image-generation AI. Cards are built from templates and real data using code, so text is always sharp, logos are never distorted, and every card is editable. AI only helps understand the request and suggest changes.
SCOPE RULE: master ID cards first. Certificates, posters and banners come only after the ID card flow is fully solid.

## 2. What the judges want
- Print-ready output: sharp at real card size, vector or high DPI, with bleed and safe margins.
- Accuracy: names, roles and IDs match the data exactly. No invented details.
- Good requirement gathering: smart follow-up questions instead of guessing.
- Design variety: 2-3 drafts that genuinely look different (layout, colors, style).
- Reliability: no overflowing text, broken layouts or stretched logos.
- Modularity: new templates, fields and design types added without rewriting code.

## 3. What the brief says NOT to do
- A wrapper around an image-generation model giving non-editable, low-resolution pictures.
- One hardcoded card design with no way to extend it.
- Garbled text, distorted logos or inconsistent layouts.
- Invented event details or names.
- Low-resolution exports, or making users finish the design in another tool.
- A generic chatbot where the design part is an afterthought.
- Jumping to posters and banners before ID cards work well.

## 4. NON-NEGOTIABLES (short list)
1. No image generation for cards. Cards are code-built SVG from a Design Spec plus real data.
2. Designs are data: a design = LAYOUT JSON (positions, sizes, elements) + THEME JSON (colors, fonts, role colors). Layouts use theme token names (background, primary, secondary, accent, text), never hex codes.
3. Everything in millimeters. Card trim 54 x 86 mm portrait (configurable), bleed 3 mm, safe margin 4 mm, canvas 60 x 92 mm, origin (0,0) at the TOP-LEFT of the canvas (not the trim line). Safe area is x 7..53, y 7..85. Font sizes in JSON are pt (1 pt = 0.352778 mm).
4. Both logos (ACM NIT Surat and SVNIT) on every card, never stretched (fit "contain"), with clear space.
5. AI is used only for: Brief extraction, style direction from words like "minimal", and turning refinement requests into Design Spec patches. AI never draws, never writes names/dates/official details, never decides required questions, never places text. Unknown values stay null and become follow-up questions. The tool must still work with sensible defaults if the AI call fails.
6. Never fix names silently. Show data problems and let the organizer decide.
7. Roles are config-driven (roles.json); differences must work in black and white, not only color.
8. QA checks run before any draft is shown and again after any change.
9. Same spec + same data = identical output (deterministic).
10. Build phase by phase; do not jump ahead.

## 5. The core idea: one Design Spec
Everything revolves around one JSON object, the Design Spec, describing one card design completely: size, colors, fonts, where each element goes, and which data field fills it.
- The AI and the user both only change the Design Spec.
- A renderer turns Design Spec + one person's data into an SVG card.
- PDF, PNG and SVG are all produced from that same SVG.
Because the spec is plain data, templates can be saved, edited in the browser, versioned and reused. A new design type (certificate, poster) is just a new spec with a different page size and elements.
Formula used in this repo: DesignSpec = layout + theme + brand kit + event info + print settings. Final card = DesignSpec + one person's data.

## 6. One-line flow
User describes need -> AI extracts a structured Brief -> tool finds missing details and asks follow-up questions -> collect assets (logos, brand colors, participant data, photos) -> validate and clean data -> generate 2-3 Design Specs (layout x theme) -> render each to SVG with real data (auto-fit text, role colors) -> automatic QA checks -> user reviews drafts, picks one, edits or refines -> export PDF / PNG / SVG, single cards or print sheets.

## 7. Tech stack
- Frontend: Next.js + Tailwind + shadcn/ui
- Editor (good-to-have): edit the Design Spec with side panels (colors, fonts, sliders), live SVG preview; Konva or Fabric.js only if drag-and-drop is wanted
- Backend: Python, FastAPI, Pydantic, pandas (CSV batch)
- Card rendering: SVG built with Jinja2 or a small Python builder; fonts embedded
- Export: CairoSVG (SVG to PDF and PNG), Pillow, pypdf or reportlab for print sheets
- Text fitting: Pillow ImageFont or fontTools to measure real text width
- QR codes: segno or qrcode (SVG output)
- Photos: Pillow for crop/resize and face-centered crop (optional OpenCV)
- AI: Gemini API with structured JSON output, only for brief extraction and refinement
- Storage: SQLite (projects, specs, versions, brand kits)

## 8. Folder structure (from the workflow document; our repo follows it)
studio/ -> backend/app/{main.py, brief/(extract, missing_info, questions), assets/(brand_kit, photo_utils), data/(csv_loader, validator), spec/(schema), templates/(layouts/*.json, themes/*.json), generator/(drafts), render/(svg_builder, text_fit, qr), qa/(overflow, logo_check, contrast), refine/(nl_to_patch), export/(pdf, png, svg, print_sheet), storage.py}, tests/, frontend/, assets/ (ACM + SVNIT logos as SVG/high-res PNG, fonts), sample_data/.

## 9. Step-by-step workflow
### Step 1: Understand the request (Brief)
The AI turns the user's plain-English request into a structured Brief with a strict schema: design_type "id_card"; event_name, tagline, dates, venue; roles [participant, organizer, mentor, volunteer]; counts {participant: 200, mentor: 20 ...}; fields_to_show [name, role, id, team, photo, qr]; card_size, orientation, style_hint. Anything not said stays null. The AI must never fill gaps with guesses.
### Step 2: Ask follow-up questions
Each design type has a list of required fields. The tool compares the Brief to that list in plain code (not AI) and asks only for what is missing: event name, tagline, dates, venue; which roles exist and how many people each; which fields appear on the card (name, role, team, ID, QR); do participants have photos, is there a data file; card size and orientation (default 54 x 86 mm portrait), lanyard hole needed. Good UX: a short form with smart defaults and tappable options, or a chat asking one thing at a time. Allow "skip" and clearly mark what stays blank.
### Step 3: Collect assets
- Logos: ACM NIT Surat and SVNIT are built in by default, stored as SVG or very high-res PNG. Never upscale a small image.
- Brand kit: logos, primary and secondary colors, fonts; switchable per event.
- Participant data: CSV or JSON (Google Forms export) with name, role, ID, team, photo link, email.
- Photos: uploaded zip or links. Missing photos get a clean placeholder or initials.
### Step 4: Validate the data
Map CSV columns to card fields (auto-guess, let the user fix). Flag missing names, unknown roles, duplicate IDs, very long names, unreadable photos. Show a summary like "235 people loaded, 12 have no photo, 3 names are very long." Never fix names silently.
### Step 5: Define the Design Spec
Example (shortened) from the workflow document:
```json
{ "page": {"width_mm": 54, "height_mm": 85.6, "bleed_mm": 3, "safe_mm": 4},
  "theme": {"fonts": {"heading": "Poppins", "body": "Inter"},
            "role_colors": {"participant": "#1F6FEB", "organizer": "#D9480F", "mentor": "#2F9E44"}},
  "elements": [
    {"type": "logo", "src": "acm_nitsurat", "x": 4, "y": 4, "w": 20, "fit": "contain"},
    {"type": "logo", "src": "svnit", "x": 30, "y": 4, "w": 20, "fit": "contain"},
    {"type": "photo", "field": "photo", "x": 12, "y": 24, "w": 30, "h": 36, "shape": "rounded"},
    {"type": "text", "field": "name", "x": 4, "y": 64, "w": 46, "max_lines": 2, "min_font": 9, "max_font": 16},
    {"type": "role_badge", "field": "role", "y": 76},
    {"type": "qr", "field": "qr_url", "x": 38, "y": 70, "w": 12} ] }
```
NOTE: this repo uses a 54 x 86 mm default (true CR80 is 85.6 mm; the document's example uses 85.6 and its PNG size note of 709 x 1082 px matches 85.6). Page size lives in PageSpec so it can be changed. With 86 mm, 300 DPI and 3 mm bleed the PNG is about 709 x 1087 px.
### Step 6: Generate 2-3 distinct drafts
Drafts must look truly different, not just recolored. Library: Layouts (3-4): Classic (logos on top, photo center), Modern split (color band on the side), Minimal (big name, small photo), Badge-style (large role strip). Themes (3-4): Clean light, Dark tech, Bold gradient, Event-brand colors. Variation rule: each draft uses a different layout AND theme, chosen by the style hint in the Brief. The generator picks 3 combinations deterministically. AI may help choose from words like "minimal" or "techy", but the output is always a valid Design Spec from our own library.
### Step 7: Role-based differentiation
Roles must be clearly different at a glance, using more than color so it works in black-and-white printing and for color-blind people: a different accent color per role; a role strip or badge with the role name in large text; optional shape or icon change (organizer gets a star, mentor a different corner mark). Roles are defined in config, so adding "Volunteer" or "Speaker" needs no code change.
### Step 8: Layout engine and text auto-fit (where most teams lose points)
- Long names: measure real text width with the actual font. Shrink from max to min font size. If still too long, wrap to a second line. If still too long, shorten safely (e.g. abbreviate the middle name) and flag it.
- Missing data: no photo -> placeholder or initials circle. Empty field -> collapse that row so the card does not look broken.
- Logos: "contain" fit with fixed aspect ratio. Never stretch. Keep minimum clear space around each logo.
- Photos: crop to the frame with face-centered cropping, never squash.
- Safe area: all text inside the safe margin so a slightly off cut does not clip it.
### Step 9: Render to SVG
Renderer reads the Design Spec and one person's data and writes SVG. Fonts embedded or converted so the printer shows exactly what we see. Photos embedded and clipped with clipPath. QR codes drawn as vector shapes. The page includes the 3 mm bleed area plus a defined trim line.
### Step 10: Automatic QA checks (run before showing any draft; a failing draft is fixed automatically or flagged)
- Text overflow: text outside its box or the safe area
- Logo ratio: logo stretched/squeezed or smaller than minimum size
- Contrast: text hard to read on its background (WCAG ratio, 4.5:1)
- Overlap: elements covering each other
- Empty fields: placeholder text like {{name}} still visible
- Data match: name or ID on the card differs from the source data
- Resolution: photo too small for print size at 300 DPI
### Step 11: Review, pick and edit
Show 2-3 drafts side by side using a real sample person from each role. User picks one; a side panel changes colors, fonts, text, logo position and size. Changes update the Design Spec and preview instantly. Save as a reusable template (no code needed).
### Step 12: Refine with natural language (good-to-have)
User types "make it more minimal" or "move the logo to the top". The AI returns a small patch to the Design Spec, never raw pixels, e.g. `[ {"op": "set", "path": "elements.0.y", "value": 4}, {"op": "set", "path": "theme.density", "value": "minimal"} ]`. The patch is validated, applied, then QA runs again; if it breaks a rule it is rejected with a message. Keep a version history for undo.
### Step 13: Export
- PDF: vector at exact physical size, with or without bleed and crop marks.
- PNG: at chosen DPI (150, 300, 600).
- SVG: fully editable vector.
- Batch: all cards as one multi-page PDF, or a ZIP of individual files.
- Print sheets: multiple cards per A4 or A3 page (e.g. 3 x 3 = 9 cards of 54 x 86 mm per A4) with crop marks and gaps.
- User-changeable settings: size, orientation, DPI, bleed on/off, color mode.

## 10. Where AI is used and not used
AI IS used for: turning the request into a structured Brief; picking style direction from words like "minimal"; turning refinement requests into Design Spec patches.
AI is NOT used for: drawing the card or generating images; writing names, dates or any official details; deciding which questions are required; placing text (the layout engine does it).
Rules: strict JSON schema output validated with Pydantic, reject and retry on invalid output; unknown stays null and becomes a follow-up question; AI output can only change fields that exist in the Design Spec; always run QA after any AI-driven change; the tool must still work with sensible defaults if the AI call fails.

## 11. Frontend screens
1. Describe: input box for the request, plus upload areas for logos, data file and photos.
2. Questions: short questions with defaults; shows what is still missing.
3. Data check: data summary and column mapping with warnings.
4. Drafts: 2-3 drafts side by side, shown with each role.
5. Editor: edit panel with live preview, refinement box, undo and version history.
6. Export: format, size, DPI, bleed, crop marks, print sheet layout, download.

## 12. Print-readiness checklist
- Card size: 54 x 86 mm default (CR80-class); also A6 badge 105 x 148 mm; configurable.
- Bleed: 3 mm extra on all sides beyond the trim line.
- Safe margin: text and logos at least 3 to 4 mm inside the trim line (we use 4).
- Resolution: 300 DPI minimum for raster; vectors preferred.
- Fonts: embedded in PDF or converted to outlines.
- Logos: SVG or high-res PNG, original aspect ratio, clear space around.
- Photos: at least 300 DPI at printed size; warn if too small.
- QR codes: vector, quiet zone included, at least 12 mm square.
- Crop marks: optional on print sheets.

## 13. Build plan (phases) with "done when"
0. Setup (ours): scaffold, project memory, toolchain proof. Done when: all checks and tests pass.
1. Single card: hardcode one SVG card with both logos, filled from a Python dict; export PDF and PNG. Done when: a real, sharp, print-ready card file comes out.
2. Design Spec: Pydantic schema, renderer that reads the spec, role colors, text auto-fit, photo clipping. Done when: changing the spec changes the card with no code edits.
3. Data: CSV loader, column mapping, validation, batch render, QR codes. Done when: 200 cards generate correctly from a CSV.
4. Drafts: 3 layouts x 3 themes, deterministic draft generator, QA validators. Done when: 3 clearly different drafts, all pass QA.
5. Brief and questions: AI extraction into Brief, missing-info logic, follow-up question UI. Done when: a sentence in produces the right questions out.
6. Frontend and export: full GUI flow, export settings, print sheets with crop marks and bleed. Done when: the complete flow works from the browser.
7. Stretch (pick 2 to 3): spec editor, NL refinement, saved templates, version history, mockup. Done when: each works reliably.
8. Polish: tests, README, sample data, rehearse demo. Done when: the demo runs with no surprises.

## 14. Testing plan
Fake CSV of 250 people with tricky cases: very long names (e.g. 45 chars) and very short names; accents or non-English characters; missing photos, tiny photos, huge photos, wrong aspect ratios; unknown or misspelled roles; empty fields (no team, no ID); duplicate IDs.
Automated tests to write over time: no rendered card has text outside its safe area; logo aspect ratio equals the original in every export; name and ID on every card equal the source row; PDF page size equals the requested physical size; PNG pixel size equals size in mm x DPI; same spec and data give identical output on two runs. Also a real test: print one sheet, cut it out, check it before the demo.

## 15. Stretch features (core first)
Batch generation with print sheets (almost required in practice); editable drafts with live preview and saved templates; natural language refinement via validated spec patches. Others if time remains: QR check-in codes, brand kit switching, version history, lanyard mockup preview, and last, certificates using the same system.

## 16. Common mistakes to avoid
Using an image-generation model for the card; skipping bleed, safe margin and DPI; stretching logos instead of aspect-ratio-preserving fit; fonts not embedded; fixed text sizes that overflow on long names; letting the AI fill missing event details; three drafts that differ only by color; building posters and banners before ID cards are perfect; never testing a real printout.

## 17. Demo script (5 minutes)
1. Type: "ID cards for our 24-hour hackathon on 18 October at SVNIT, with 200 participants, 20 mentors, 15 organizers."
2. Show the tool asking only for what is missing (event name, tagline, fields, photos).
3. Upload the CSV and photos; show the data-check summary with warnings.
4. Show 3 distinct drafts, each with participant, organizer and mentor versions.
5. Pick one, edit a color and the logo position, then try "make it more minimal".
6. Show a person with a very long name and one with no photo, and how the layout adapts.
7. Export a single card as PDF, PNG at 300 DPI and SVG; change size and DPI settings.
8. Export a print sheet with crop marks for all 235 cards and show the printed paper.
9. Show how a new role or a new template is added without code changes.

## 18. Team and working method (project-specific decisions)
- The developer is a student with basic Python (up to file reading and CSV) and basic OpenCV; code must be simple and readable.
- Work is done phase by phase. Claude writes or builds each phase and reviews the results before the next phase starts.
- A teammate designs the real layouts and themes in Figma and writes them as JSON (3 layouts x 3 themes). She uses `python scripts/preview.py <layout> <theme>` to validate her files. Layout and theme files live in backend/app/templates/layouts and backend/app/templates/themes.
- Layouts: Classic, Modern split, Minimal. Themes: Clean light, Dark tech, Bold event. Any layout must work with any theme.
- Git: main always works; feature branches; pull requests; small commits.
