# Rendering and Export Module — Progress Report

## 1. Summary

- This repository contains the Python rendering and export module for Person 2 of the Incursion Track 4 project.
- It renders cards from a temporary Design Spec, JSON layouts/themes, and people records; it supports SVG, PDF, PNG, ZIP batches, and A4/A3 sheets.
- Six phases are present, with verifiers for Phases 1–5B and API/test/documentation work in Phase 6.
- The latest local `verify_all.py` run passed all seven steps: pytest and the six phase verifiers.
- Main risks are placeholder branding/design data, no physical print test, and a temporary spec format awaiting Person 1.
- FastAPI and Next.js integration, natural-language extraction, and final designer-approved artwork are not in this repository.

## 2. What was built, phase by phase

| Phase | What it does | Key files | Evidence |
|---|---|---|---|
| 1 — Single card export | Builds a hardcoded 54 x 86 mm trim card with 3 mm bleed and writes SVG, PDF, and PNG. | `render/phase1_card.py` | `verify_phase1.py` checks SVG geometry, PDF size, PNG dimensions, and whether logos are embedded or placeholders. |
| 2 — Spec-driven renderer | Renders SVG cards from normalized spec values, role, selected layout, and theme. It includes classic/split layouts and blue/dark themes. | `render/renderer.py`, `render/spec_adapter.py`, `render/loaders.py`, `templates/layouts/`, `templates/themes/` | `verify_phase2.py` renders sample records, compares layouts/themes, checks role-color/cue distinctions including grayscale, and checks spec access through the adapter. |
| 3 — Text, photos, QR | Uses font metrics to fit/wrap/shorten text; crops photos without distorting them and uses initials for missing photos; builds QR codes as SVG paths when a real URL base and ID exist. | `render/text_fit.py`, `render/photo.py`, `render/qr.py` | `verify_phase3.py` checks long-name fitting/shortening, accented text, photo crops/fallback, vector QR, card size, and PDF/PNG output. |
| 4 — QA | Runs seven checks: text overflow, logo aspect ratio, contrast, overlap, empty fields, data match, and resolution. | `qa/checks.py`, `qa/report.py` | `verify_phase4.py` runs the checks on bundled people. `tests/test_qa.py` exercises individual detections and JSON-friendly reports. |
| 5A — Batch export | Validates CSV/JSON people rows; supports SVG/PDF/PNG, DPI, orientation, and bleed; exports each valid person into a ZIP with `report.json`. | `export/settings.py`, `export/csv_loader.py`, `export/exporters.py`, `export/batch.py`, `export/cli.py` | `verify_phase5a.py` checks formats/settings and a 250-row CSV; `tests/test_export.py` tests loaders, formats, reports, and settings. |
| 5B — Print sheets | Places cards on centered A4/A3 sheets, supports portrait/landscape and bleed/trim, draws crop marks, and makes a vector PDF. | `export/print_sheet.py`, `export/cli.py` | `verify_phase5b.py` checks page dimensions, capacities, geometry, vector PDF/fonts, no-crop-marks, and 246 valid sample records; `tests/test_print_sheet.py` covers layout and exports. |
| 6 — Team integration | Adds stable wrapper functions, exact pins for direct project/test dependencies, combined verification, pytest configuration, and format/API documentation. | `export/api.py`, `render/spec_adapter.py`, `requirements.txt`, `verify_all.py`, `pytest.ini`, `docs/formats.md`, `README.md` | `tests/test_api.py` smoke-tests the public functions. The Phase 6 work is also present in the latest commit. |

The verifier checks the bundled examples and temporary formats. They do not prove integration against Person 1's future schema or Person 4's final artwork.

## 3. Repository map

| Path | Purpose |
|---|---|
| `assets/` | Logo drop location and instructions. No real logo files are present. |
| `docs/` | Data-format documentation and this report. |
| `export/` | Public API, settings, single-card exporters, batch ZIP, CSV/JSON loader, CLI, and print-sheet composer. |
| `qa/` | QA rules, `Issue` model, and report formatting. |
| `render/` | Spec adapter, SVG renderer, template loaders, text fitting, photo, and QR helpers; `phase1_card.py` is the initial single-card renderer. |
| `sample_data/` | Bundled eight-person JSON sample, photos, and 250-row CSV fixture. |
| `sample_output/` | Local generated sample artifacts. The directory is ignored by Git and its files are not tracked. |
| `specs/` | `temp_spec.json`, the current temporary Design Spec. |
| `templates/layouts/` | `classic.json` and `split.json` layout templates. |
| `templates/themes/` | `blue.json` and `dark.json` theme templates. |
| `tests/` | API, export, print-sheet, and QA tests. |
| `tools/` | CSV fixture generator. |
| `render_demo.py` | Renders bundled JSON people to SVG/PDF/PNG under `sample_output/phase2/`. |
| `verify_phase1.py` … `verify_phase5b.py` | Phase-specific verification scripts. |
| `verify_all.py` | Runs pytest followed by the six phase verifiers and summarizes status/time. |
| `requirements.txt` | Exact pins for CairoSVG, Pillow, pypdf, fonttools, segno, and pytest. |
| `pytest.ini` | Makes pytest discover tests under `tests/`. |

## 4. Public API

The functions below are defined in `export/api.py`. Inputs named `spec` and `person` accept normalized adapter models or decoded JSON mappings.

| Function | Inputs | Output |
|---|---|---|
| `render_card_svg(spec: SpecInput, person: PersonInput) -> str` | Spec, one person | SVG text |
| `render_preview_svg(spec: SpecInput, role: str) -> str` | Spec, supported role | SVG for the bundled sample person of that role |
| `run_qa_for_card(spec: SpecInput, person: PersonInput) -> list[dict[str, str \| None]]` | Spec, one person | JSON-friendly QA issue list |
| `export_card_bytes(spec: SpecInput, person: PersonInput, settings_dict: Mapping[str, Any]) -> bytes` | Spec, person, `ExportSettings` mapping | SVG/PDF/PNG bytes |
| `export_batch_zip(spec: SpecInput, people: Sequence[PersonInput], settings_dict: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]` | Spec, people, `ExportSettings` mapping | ZIP bytes and report |
| `export_print_sheet_pdf(spec: SpecInput, people: Sequence[PersonInput], paper: str, settings_dict: Mapping[str, Any]) -> tuple[bytes, dict[str, Any]]` | Spec, people, `"A4"`/`"A3"`, `PrintSheetSettings` mapping | PDF bytes and report |
| `load_people_file(path: str \| Path) -> tuple[list[spec_adapter.Person], list[dict[str, int \| str]]]` | CSV or JSON path | Normalized people and validation problems |
| `list_layouts() -> list[str]` | None | Sorted layout filename stems |
| `list_themes() -> list[str]` | None | Sorted theme filename stems |

These wrappers do not load a Design Spec file. File loading and field normalization belong to `render/spec_adapter.py`. Invalid input can raise `ValueError`; underlying filesystem, conversion, and native-library failures can also propagate.

## 5. How to install and run

Windows setup, as documented in `README.md`:

```powershell
winget install MSYS2.MSYS2
```

In the MSYS2 UCRT64 terminal:

```bash
pacman -Syu
pacman -S mingw-w64-ucrt-x86_64-gtk3
```

In PowerShell from the repository:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:Path = "C:\msys64\ucrt64\bin;$env:Path"
python -m pip install -r requirements.txt
python -c "import cairosvg; print(cairosvg.__version__)"
```

The README documents Linux/macOS Cairo installation followed by the same requirements install:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -c "import cairosvg; print(cairosvg.__version__)"
```

Run the demo, batch, sheet, tests, and all verifiers:

```powershell
python render_demo.py
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --format pdf --out out\batch.zip
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --sheet A4 --out out\sheet_a4.pdf
python -m pytest
python verify_all.py
```

Expected outputs: demo cards in `sample_output\phase2\`, a batch ZIP and print-sheet PDF under `out\`, passing pytest, and a verification summary. **Clean-checkout caveat:** `verify_phase1.py` reads `sample_output/card.svg`, `.pdf`, and `.png`, but `sample_output/` is ignored and those files are not tracked. On a fresh checkout, first run `python -m render.phase1_card` to create those files; that command is not included in `verify_all.py`.

## 6. Verification results

I ran `python verify_all.py` in this repository. It exited successfully. Its actual summary:

| Step | Result | Runtime |
|---|---:|---:|
| pytest | PASS | 48.00 s |
| `verify_phase1.py` | PASS | 0.37 s |
| `verify_phase2.py` | PASS | 13.77 s |
| `verify_phase3.py` | PASS | 5.90 s |
| `verify_phase4.py` | PASS | 6.04 s |
| `verify_phase5a.py` | PASS | 283.85 s |
| `verify_phase5b.py` | PASS | 173.44 s |
| **All steps** | **7/7 PASS** | **531.38 s** |

`python -m pytest --collect-only -q` collected **50 tests**. The latest full pytest run inside `verify_all.py` passed.

Measured facts from the phase verifiers and a separate run of `verify_phase5a.py`:

- At 300 DPI with bleed, PNG output is **709 x 1087 pixels**. Trim-only PNG is **638 x 1016 pixels**. Evidence: `verify_phase5a.py`.
- Single-card vector PDF is **170.08 x 260.79 pt**, with embedded fonts detected. Evidence: `verify_phase5a.py`.
- Print sheets pass A4 portrait **595.28 x 841.89 pt**, A3 portrait **841.89 x 1190.55 pt**, and landscape dimension swapping. Evidence: `verify_phase5b.py`.
- Computed cards per page are the same with and without bleed for the checked 54 x 86 mm trim card: A4 portrait **4**, A4 landscape **4**, A3 portrait **12**, A3 landscape **10**. The orientations differ in rows/columns: A4 landscape is 4 x 1; A3 landscape is 5 x 2. Evidence: `verify_phase5b.py` and a direct call to `print_sheet_layout`.
- `sample_data/test_250.csv` has **246 exported valid rows** and **4 skipped rows**: CSV row 21 missing name; row 22 unsupported role `unknown`; row 23 missing ID; row 26 duplicate ID `P001`. The Phase 5A verifier observed **0 export failures**.
- In a separate direct Phase 5A verification run, its 250-row batch operation took **277.27 s**. The whole Phase 5A verifier took **283.85 s** inside `verify_all.py`; these are different measurements.
- The Phase 5B verifier reported **246 valid cards on 62 A4 portrait pages**, or 4 per page, and detected embedded fonts and vector page content. It also reported the crop-mark gap calculation as 9.25 mm with bleed and 15.25 mm without bleed.
- Phase 4's verifier passed each of its seven checks on the eight bundled sample people. This is not a check of production attendee data or final designer assets.

## 7. Requirements coverage

Statuses describe evidence in this repository only. “Not in my scope” means the requirement is assigned to another role or product layer; it does not mean the project as a whole cannot implement it.

| Requirement | Status | Evidence and note |
|---|---|---|
| Frontend GUI for the full workflow (Person 3) | Not in my scope | No Next.js/frontend application files are present. |
| Accepts a natural-language request and drives the workflow (Person 1) | Not in my scope | No FastAPI service, brief extraction, or Gemini integration is present. |
| Asks follow-up questions instead of fabricating details (Person 1) | Not in my scope | No conversational backend/brief workflow is present. The renderer deliberately uses visible fallbacks or omits a QR for missing values. |
| Generates 2–3 distinct design drafts | Partly met | Two selectable layout files exist (`classic`, `split`); `verify_phase2.py` confirms distinct rendered output. There is no draft-generation or review workflow. The current layouts are marked `_placeholder`. |
| Multiple ID card roles, visually differentiated including black and white | Met for bundled templates | `verify_phase2.py` checks four roles have different outputs and grayscale cue shapes; role labels/colors/cues are in `render/renderer.py`. Final artwork approval is not verified. |
| High-resolution, print-suitable output | Partly met | `verify_phase1.py` and `verify_phase5a.py` check 300-DPI pixel output and vector PDFs with embedded fonts. No physical print test has been done. Photos remain raster images inside otherwise vector artwork. |
| More than one export format with tunable size, DPI, and orientation | Met for implemented settings | `export/settings.py`, `export/exporters.py`, and `tests/test_export.py` cover SVG/PDF/PNG, DPI, orientation, bleed/trim. No proofing against a production printer is present. |
| ACM NIT Surat and SVNIT logos with correct placement/proportions and no distortion | Not met yet | `assets/README.md` requests `acm.svg`/`.png` and `svnit.svg`/`.png`; only `assets/README.md` exists. `verify_phase1.py` identifies placeholders. Actual brand placement/proportions cannot be confirmed. |
| Cards populated from real provided data, accurate and consistent | Partly met | CSV/JSON loaders and `data_match` QA are implemented; tests/verifiers use bundled sample fixtures. The 250 CSV is a test fixture, not verified production attendee data. |
| Modular code; new designs/templates/fields can be added | Partly met | `export/api.py`, `render/spec_adapter.py`, and JSON layout/theme loaders provide boundaries; `verify_phase2.py` confirms theme/layout changes affect output. New fields still require adapter/render support, and the real schema is pending. |
| Reliable output: validated, no overflowing text, broken layouts, or invented details | Partly met | Seven QA checks and tests exist; bundled Phase 4 checks pass. Long names may be shortened; missing values can render explicit placeholders; warnings remain. No universal or print-production guarantee is established. |
| Good to have: batch CSV/JSON generation and print sheets | Met for existing fixture behavior | `export/csv_loader.py`, `export/batch.py`, `export/print_sheet.py`, `verify_phase5a.py`, and `verify_phase5b.py`. |
| Good to have: QR codes | Partly met | Vector QR path tested by `verify_phase3.py` with a non-null URL; the bundled temporary spec has a null URL, so its QR is intentionally skipped. |
| Good to have: bleed and crop marks | Met by code and geometry checks | `export/print_sheet.py` and `verify_phase5b.py` cover bleed/trim, marks, and computed clearances. Visual and physical print quality is not verified. |
| Good to have: long-name/missing-photo/field adaptation | Partly met | `render/text_fit.py` shrinks/wraps/shortens; `render/photo.py` uses initials fallback; text data has visible missing-value fallback. This does not dynamically reflow the whole layout. |

## 8. Known issues and limitations

- **Brand assets:** `assets/` contains only `README.md`. Both ACM NIT Surat and SVNIT are placeholders. The logo aspect-ratio QA cannot confirm the real logos until files arrive.
- **Temporary values:** `specs/temp_spec.json` has a null event name and no non-null `attendance_url_base`. The card displays `EVENT NAME`; QR rendering is skipped by design.
- **Temporary schema:** this is a temporary Design Spec, not Person 1's final schema. `docs/formats.md` says to adapt `render/spec_adapter.py` when the real contract arrives; this integration has not been verified.
- **Layouts/themes:** `classic.json`, `split.json`, `blue.json`, and `dark.json` are marked `_placeholder`. They are working template examples, not verified final designer deliverables.
- **Print-sheet visual spacing:** the Phase 5B geometry verifier reports numeric crop-mark clearances. The concern that card edges and marks look too close when viewed was provided as project context; I did not conduct a separate visual inspection or investigate it. No real printout test has been done.
- **Long name:** `verify_phase3.py` confirms the bundled long name fits the measured text box by shortening it. The final visual treatment and design acceptance are not verified.
- **Batch speed:** the measured sample batch took 277.27 seconds for 250 input rows (246 exports and four skipped). Performance on other machines/formats/data is not verified.
- **Print-sheet geometry:** `export/print_sheet.py` computes grid card dimensions from fixed 60 x 92 mm bleed / 54 x 86 mm trim values and a 3 mm bleed assumption. `spec_adapter.py` can represent other dimensions, but custom dimensions on sheets have not been verified.
- **Batch QA policy:** `export/batch.py` records QA issues in the report but still exports a card unless rendering/export raises an exception. The print-sheet exporter skips QA-error cards. The policies differ.
- **Sample-output verifier precondition:** Phase 1 outputs are ignored and untracked; the Phase 1 verifier expects them to exist. The current `verify_all.py` run passed because they were already present locally. Clean-clone verification is not established without first running `python -m render.phase1_card`.
- **Fonts/runtime:** `requirements.txt` pins six direct packages. CairoSVG's native Cairo/GTK runtime is an OS dependency and must be installed separately on Windows; transitive Python requirements are not a complete lockfile.
- **No TODO markers:** a repository search of Python files found no `TODO`, `FIXME`, `XXX`, or `NotImplemented` markers.
- **External-team integration:** no running FastAPI/Next.js application or production API contract was available in this repository; integration is not verified.

## 9. Dependencies on teammates

| Teammate | Needed by this module | What this module offers |
|---|---|---|
| Person 1 — backend | Final Design Spec shape, agreed people/photo schema, required fields and null semantics, and endpoint expectations. | Normalized `DesignSpec`/`Person` access in `render/spec_adapter.py`; public wrappers in `export/api.py`; JSON-friendly QA/export reports. |
| Person 3 — frontend | Agreed backend request/response contract, supported formats/settings, and error/report display expectations. | SVG/PDF/PNG/ZIP bytes, print-sheet PDF, template lists, QA dictionaries, and people validation via `export.api`. |
| Person 4 — designer | Final layout/theme JSON, real logos with source dimensions/viewBoxes, chosen font families, and reviewed print-safe designs. | `templates/layouts/`, `templates/themes/`, and `assets/` loading paths; renderer/QA; sample fixtures and verification commands. |

## 10. Suggested next steps (rough estimates)

Effort estimates are guesses and exclude teammate review time.

1. **Agree and integrate Person 1's real schema** — 0.5–2 days after schema delivery. Change/extend the adapter and verify all public wrappers with the agreed contract.
2. **Deliver final design assets** — 1–3 days, depending on review cycles. Person 4 supplies layouts/themes, actual logo files, and font requirements; run QA on those files.
3. **Investigate sheet spacing visually and print a test sheet** — 0.5–1 day. Compare crop positions, bleed, printer scaling, and physical trimming; adjust geometry only after measuring.
4. **Connect the API to the backend and frontend** — 1–3 days after the endpoint contract is agreed. Exercise downloads, settings, QA summaries, and invalid-row reports end to end.
5. **Revisit QA with representative production data** — 0.5–2 days. Review long-name truncation, data matches, contrast, missing-photo fallbacks, and any real failures.
6. **Improve batch runtime only if needed** — 0.5–2 days. Profile current rendering/QA/export before changing behavior; current measured runtime is about 4 minutes 37 seconds for this fixture.
7. **Make combined verification reproducible from a clean clone** — 0.25–0.5 day. Make Phase 1 artifacts a verifier prerequisite or have the combined runner create them, then check from a clean checkout.

## 11. Repository state

- Branch: `arvind`.
- Latest commit observed: `45ea4d5 Phase 6: public API, pinned requirements, verify_all, docs`.
- Before creating this report, `git status` was clean and the branch was up to date with `origin/arvind`.
- After this report is added, the worktree will not be clean: `docs/PROGRESS_REPORT.md` is the sole intended new file; no code, tests, layouts, or themes were changed for this report.
