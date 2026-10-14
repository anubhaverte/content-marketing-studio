# content-marketing-studio

## QA checks

`qa.run_qa` checks measured text overflow and truncation, logo proportions, WCAG text contrast, unintended layout overlaps, missing source fields and fallback use, rendered data matching, and PNG resolution at the requested DPI (300 by default). Results include a check name, severity, person ID, and plain-language message; `qa.report` formats readable output or JSON-friendly dictionaries.

Run the Phase 4 checks and focused tests:

```powershell
python -m pytest tests\test_qa.py
python verify_phase4.py
```

Expected result: pytest passes. Verification prints each person's issues and a `PASS`/`FAIL` line per check; with the bundled samples it currently reports text overflow for person-003 and low contrast for person-005, then exits nonzero. Placeholder logos and intentional shortening appear as warnings.

## Export

```powershell
python tools\make_test_csv.py
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --format pdf --dpi 300 --out out\batch.zip
python verify_phase5a.py
```

Expected result: the CLI writes a ZIP with one PDF per valid person and `report.json`, prints totals, skipped rows, and elapsed time; Phase 5A verification prints `PASS` for the export checks.

## Print sheets

```powershell
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --sheet A4 --out out\sheet_a4.pdf
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --sheet A3 --no-crop-marks --no-bleed --landscape --out out\sheet_a3_landscape.pdf
python verify_phase5b.py
python -m pytest tests\test_print_sheet.py
```

Expected result: each command writes a vector PDF, the CLI prints cards per page, page count, and elapsed time, and Phase 5B verification and tests print `PASS` and pass.
