# Content Marketing Studio card renderer

This Python module renders event badges from a Design Spec, attendee data, a layout, and a theme. It produces SVG artwork, vector PDFs, PNGs, batch ZIP archives, and print sheets. It also checks cards with automated QA rules. Layout and theme files can be added without changing Python code.

The stable functions for application integrations are in `export.api`. They accept the normalized `DesignSpec` and `Person` models or decoded JSON objects for those inputs, and return SVG strings, bytes, or JSON-friendly reports. See [docs/formats.md](docs/formats.md) for the exact data shapes.

## Install on Windows

Install MSYS2 and its UCRT64 GTK runtime. GTK provides the Cairo native DLL needed by CairoSVG:

```powershell
winget install MSYS2.MSYS2
```

Open the **MSYS2 UCRT64** terminal and run:

```bash
pacman -Syu
pacman -S mingw-w64-ucrt-x86_64-gtk3
```

In PowerShell, from the project folder, create the Python environment, expose the Cairo DLL directory, install the pinned requirements, and check CairoSVG:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:Path = "C:\msys64\ucrt64\bin;$env:Path"
python -m pip install -r requirements.txt
python -c "import cairosvg; print(cairosvg.__version__)"
```

Expected result: CairoSVG prints `2.9.1` without a Cairo DLL error. Keep the MSYS2 UCRT64 `bin` directory on `PATH` in any shell that runs PDF/PNG exports.

## Install on Linux or macOS

Install Cairo (`sudo apt-get install libcairo2` on Debian/Ubuntu; `brew install cairo` on macOS), then install the pinned Python requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -c "import cairosvg; print(cairosvg.__version__)"
```

## Run

Render the bundled sample people to SVG, PDF, and PNG:

```powershell
python render_demo.py
```

Expected result: output files are written under `sample_output\phase2\`.

Export one PDF per valid person into a ZIP (the `--format` selects the card file format inside the ZIP):

```powershell
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --format pdf --out out\batch.zip
```

Expected result: `out\batch.zip` contains each exported card and a `report.json`; the CLI prints export totals and elapsed time.

Create a print sheet:

```powershell
python -m export.cli --spec specs\temp_spec.json --people sample_data\test_250.csv --sheet A4 --out out\sheet_a4.pdf
```

Expected result: a vector PDF is written; the CLI prints cards per page, pages, skipped/failed people, and elapsed time. Use `--sheet A3`, `--no-crop-marks`, `--no-bleed`, or `--landscape` to select other supported sheet settings.

Run the tests and all verification scripts:

```powershell
pytest
python verify_all.py
```

Expected result: pytest passes; `verify_all.py` then runs `verify_phase1.py` through `verify_phase5b.py` in order and prints a `PASS` or `FAIL` summary and total elapsed time.

## Public API

Import the stable functions from `export.api`. Supply a `DesignSpec`/`Person` from `render.spec_adapter` or a decoded JSON object. Settings are dictionaries. Functions do not read the Design Spec file themselves; use `render.spec_adapter.load_design_spec` for file input.

| Function | Inputs | Output |
|---|---|---|
| `render_card_svg(spec, person)` | Design Spec and one person | SVG `str` |
| `render_preview_svg(spec, role)` | Design Spec and supported role | SVG `str` for the bundled sample person |
| `run_qa_for_card(spec, person)` | Design Spec and one person | list of issue dictionaries |
| `export_card_bytes(spec, person, settings_dict)` | Design Spec, person, `ExportSettings` dict | SVG/PDF/PNG `bytes` |
| `export_batch_zip(spec, people, settings_dict)` | Design Spec, people, `ExportSettings` dict | `(ZIP bytes, report dict)` |
| `export_print_sheet_pdf(spec, people, paper, settings_dict)` | Design Spec, people, `A4`/`A3`, print-sheet settings dict | `(PDF bytes, report dict)` |
| `load_people_file(path)` | CSV or JSON path | `(Person list, problem list)` |
| `list_layouts()` | — | sorted layout-name list |
| `list_themes()` | — | sorted theme-name list |

Invalid inputs raise `ValueError`; underlying OS, native-library, and export errors are reported by the existing functions. Batch and print-sheet reports retain per-person QA details.

## Known limitations

- The ACM and SVNIT marks are labeled placeholders until their real SVG or PNG files are added to `assets/`.
- The bundled Design Spec intentionally has a null event name, so the card renderer displays its visible `EVENT NAME` placeholder. A null `attendance_url_base` intentionally omits the QR code.
- Batch export renders and runs QA for each card; a 250-row batch takes several minutes on a typical development machine. The actual time depends on machine and export format.
- Photos in people files are local paths relative to that input file and must remain beneath its directory.
