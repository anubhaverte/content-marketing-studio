# ID Card Studio (content-marketing-studio)

A design tool that turns a plain-English request into print-ready ID cards (PDF, PNG, SVG) for college events. Cards are built from layout and theme JSON files plus real data, using code. No image generation. Built for the ACM NIT Surat hackathon (Track 4).

Read `docs/PROJECT_CONTEXT.md` for the full project description and rules.

## Prerequisites
- Python 3.10 or newer
- Git
- The Cairo graphics library (needed by CairoSVG):
  - Windows: install the GTK3 runtime, or use WSL, or `conda install cairo`
  - macOS: `brew install cairo`
  - Ubuntu/Debian: `sudo apt install libcairo2`

## Setup
From the repo root:

```
python -m venv .venv
```
Activate it:
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`
- macOS/Linux: `source .venv/bin/activate`

Then install and check:
```
cd backend
pip install -r requirements.txt
python scripts/check_env.py
```

## Command cheat sheet (run from `backend/` with the venv active)

| Task | Command |
|---|---|
| Check the environment | `python scripts/check_env.py` |
| Run all tests | `python -m pytest` |
| Render the hello card | `python scripts/hello_card.py` (writes to `output/`) |
| Make the 250-row sample data | `python scripts/make_sample_data.py` (writes to `sample_data/`) |
| Validate a layout + theme | `python scripts/preview.py app/templates/layouts/classic.json app/templates/themes/clean_light.json` |
| Start the API | `uvicorn app.main:app --reload`, then open http://127.0.0.1:8000/docs |

## Folder map
```
backend/app/       FastAPI app and all logic (spec, render, export, data, qa, brief, generator, refine)
backend/app/templates/layouts  layout JSON files (where things go)
backend/app/templates/themes   theme JSON files (colors and fonts)
backend/scripts/   helper scripts
backend/tests/     automated tests
frontend/          Next.js app (Phase 6)
assets/            logos (placeholders for now), fonts, artwork
sample_data/       generated test CSV and photos
output/            generated files (git-ignored)
docs/              project context, conventions, phase checklist
```

## QA checks (Phase 4)

`qa.run_qa` checks measured text overflow and truncation, logo proportions, WCAG text contrast, unintended layout overlaps, missing source fields and fallback use, rendered data matching, and PNG resolution at the requested DPI (300 by default). Results include a check name, severity, person ID, and plain-language message; `qa.report` formats readable output or JSON-friendly dictionaries.

Run the Phase 4 checks and focused tests:

```powershell
python -m pytest tests\test_qa.py
python verify_phase4.py
```

Expected result: pytest passes. Verification prints each person's issues and a `PASS`/`FAIL` line per check; with the bundled samples it currently reports text overflow for person-003 and low contrast for person-005, then exits nonzero. Placeholder logos and intentional shortening appear as warnings.

## Export (Phase 5A)

```powershell
python tools\make_test_csv.py
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --format pdf --dpi 300 --out out\batch.zip
python verify_phase5a.py
```

Expected result: the CLI writes a ZIP with one PDF per valid person and `report.json`, prints totals, skipped rows, and elapsed time; Phase 5A verification prints `PASS` for the export checks.

## Notes
- The logos in `assets/logos/` are PLACEHOLDERS. Replace them with the real ACM NIT Surat and SVNIT logos using the same file names.
- The starter layout and theme are developer examples. The teammate's real designs will replace them.

## Team workflow
- `main` always works.
- Work on a branch named `feature/<thing>`, make small commits, open a pull request, and have someone look at it before merging.
