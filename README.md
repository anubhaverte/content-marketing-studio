# content-marketing-studio

## QA checks

`qa.run_qa` checks measured text overflow and truncation, logo proportions, WCAG text contrast, unintended layout overlaps, missing source fields and fallback use, rendered data matching, and PNG resolution at the requested DPI (300 by default). Results include a check name, severity, person ID, and plain-language message; `qa.report` formats readable output or JSON-friendly dictionaries.

Run the Phase 4 checks and focused tests:

```powershell
python -m pytest tests\test_qa.py
python verify_phase4.py
```

Expected result: pytest passes. Verification prints each person's issues and a `PASS`/`FAIL` line per check; with the bundled samples it currently reports text overflow for person-003 and low contrast for person-005, then exits nonzero. Placeholder logos and intentional shortening appear as warnings.
