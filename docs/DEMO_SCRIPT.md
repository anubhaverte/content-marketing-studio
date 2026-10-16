# Five-minute design demo

## 0:00–0:40 — Introduce the system

Show that card geometry and theme colors are JSON, separate from attendee
records. Explain that the local renderer is a temporary stand-in for the
production renderer.

## 0:40–1:40 — Compare three distinct drafts

Open `studio/sample_data/contact_sheet.png`. Point out classic portrait,
modern split band, and minimal editorial layouts across clean-light, dark-tech,
and bold-event themes. The same layout can use each theme without code changes.

## 1:40–2:30 — Show a long name

Display the long-name column. Verify that the 45+ character name wraps or
scales within its text box without overlapping other card elements.

## 2:30–3:10 — Show missing-photo behavior

Display the no-photo column. The temporary preview uses a labeled placeholder
instead of failing; the production renderer can replace that fallback policy.

## 3:10–4:10 — Add a theme without code changes

Copy a theme JSON, change its palette and font paths, define all role colors
and monochrome badge styles, then run the contrast and role checks. Select the
new theme in the contact-sheet workflow.

## 4:10–5:00 — Close with quality checks

Run `python studio\design_tools\run_all_checks.py`, show the print-test steps,
and scan a sample QR code. Call out that real institutional logo assets and the
production renderer still need to be integrated.
