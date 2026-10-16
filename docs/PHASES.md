# Phases

Tick a box only when its "done when" condition is really met.

## Phase 0: Setup and toolchain proof
Done when: environment check passes, tests pass, hello card renders to a PDF/PNG of the right physical size.
- [x] Folder structure follows the workflow document
- [x] Project memory saved (docs/PROJECT_CONTEXT.md, AGENTS.md, GEMINI.md)
- [x] Pydantic schema for layouts, themes, people, brand kit, Design Spec, Brief
- [x] Layout/theme loaders with friendly error messages
- [x] Starter layout, starter theme, roles.json
- [x] Jinja2 -> SVG -> CairoSVG -> PDF/PNG proof (60 x 92 mm; 709 x 1087 px at 300 DPI)
- [x] 250-row messy sample data with ground-truth counts
- [x] check_env.py, preview.py (validation only), API /health
- [x] Tests pass

## Phase 1: Single card
Done when: a real, sharp, print-ready card file comes out.
- [ ] One hardcoded SVG card, both real logos, real fonts embedded, filled from a Python dict
- [ ] PDF and PNG export

## Phase 2: Design Spec
Done when: changing the spec changes the card with no code edits.
- [ ] merge_design_spec (layout + theme + brand kit + event)
- [ ] Renderer for every element type, role colors, text auto-fit, photo clipping
- [ ] preview.py renders preview.png

## Phase 3: Data
Done when: 200 cards generate correctly from a CSV.
- [ ] CSV loader and column mapping
- [ ] Validation against expected_issues.json
- [ ] Batch render, QR codes, face-centered photo crops

## Phase 4: Drafts
Done when: 3 clearly different drafts, all pass QA.
- [ ] 3 layouts x 3 themes
- [ ] Deterministic draft generator
- [ ] QA validators (overflow, logo ratio, contrast, overlap, empty fields, data match, resolution)

## Phase 5: Brief and questions
Done when: a sentence in produces the right questions out.
- [ ] Gemini extraction into Brief (with fallback if AI fails)
- [ ] Missing-info logic and follow-up questions

## Phase 6: Frontend and export
Done when: the complete flow works from the browser.
- [ ] Next.js screens: Describe, Questions, Data check, Drafts, Editor, Export
- [ ] Export settings, print sheets with crop marks and bleed

## Phase 7: Stretch (pick 2 to 3)
- [ ] Editable drafts / saved templates / NL refinement / version history / mockup

## Phase 8: Polish
Done when: the demo runs with no surprises.
- [ ] Tests, README, sample data, rehearsed demo, real printout
