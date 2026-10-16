# Design workflow

Card layouts are in `studio/backend/app/templates/layouts/`; themes are in
`studio/backend/app/templates/themes/`. The stand-in renderer loads both JSON
files at runtime, so a new layout or theme can be added without renderer code
changes as long as it follows [FORMAT.md](./FORMAT.md).

## Add a layout

1. Copy the closest layout JSON and give it a unique `id` and descriptive `name`.
2. Follow `FORMAT.md`, use semantic color tokens, preserve canvas/safe-area
   rules, and include both logos and a QR code.
3. Give optional `team` and `id_number` rows their documented collapse metadata.
4. Run `python studio\design_tools\validate_layouts.py` and preview the result.

## Add a theme

1. Copy a theme JSON, set valid hex values for every named color, and ensure
   text/background combinations meet the contrast minimum.
2. Include heading/body font paths, role colors for all three roles, and
   distinct role badge shapes, border styles, and labels.
3. Download the font files listed in [`../studio/docs/FONTS.md`](../studio/docs/FONTS.md).
4. Run `python studio\design_tools\check_contrast.py` and
   `python studio\design_tools\check_roles_bw.py`.

## Run the local workflow

From the repository root:

```powershell
python studio\design_tools\run_all_checks.py
python studio\design_tools\make_test_photos.py
python studio\design_tools\make_test_csv.py
python studio\design_tools\preview_local.py
python studio\design_tools\make_contact_sheet.py
```

The previews are explicitly a **temporary stand-in** until the renderer
teammate's production implementation is available. Install Pillow, CairoSVG,
and `qrcode` in the selected Python environment (`python -m pip install
Pillow CairoSVG qrcode`). On Windows, CairoSVG may also need a native Cairo
runtime; when that is unavailable the preview uses its Pillow fallback.
Preview outputs go under `studio/sample_data/`.

The attendee adapter maps CSV `name` to layout `full_name` and CSV `id` to
`id_number`. It leaves unknown organization data empty and creates a
clearly-test-only QR payload (`TEST-ID-<id>` or a row-specific missing-ID
payload); neither is production event information. Missing or unreadable
photos use a labeled placeholder.

The repository does not include official logo artwork or the Google Font
binaries. Import approved ACM NIT Surat and SVNIT raster logos as
`studio/assets/logos/acm_nit_surat.png` and `studio/assets/logos/svnit.png`,
and download the listed font files and OFL notices described in
[`../studio/docs/FONTS.md`](../studio/docs/FONTS.md). Until then, the preview
uses text logo stand-ins and system font fallbacks. A Figma URL/design file
and the physical 100%-scale print/QR scan must be supplied or completed by
the team; neither exists in this repository.

## Handoff notes

- **Person 1 — validation:** maintain schema, safe-area, contrast, and role
  checks; review invalid roles, duplicate/missing IDs, and CSV field mapping.
- **Person 2 — text fit and photo handling:** test long and multilingual names,
  photo crops, missing/corrupt photos, and large images. Replace the temporary
  renderer, text logo stand-ins, and font fallbacks with the production pipeline.
