# Project rules: ID Card Studio (Track 4, ACM NIT Surat Hackathon)

At the start of every session and before starting any phase, read docs/PROJECT_CONTEXT.md and docs/PHASES.md.

## Non-negotiables
1. No image generation for cards: code-built SVG from a Design Spec plus real data.
2. Designs are data: LAYOUT JSON + THEME JSON. Layouts use theme token names (background, primary, secondary, accent, text), never hex.
3. Everything in mm. Trim 54 x 86, bleed 3, safe 4, canvas 60 x 92, origin top-left of the canvas. Safe area x 7..53, y 7..85. Fonts in pt.
4. Both logos (ACM NIT Surat, SVNIT) on every card, never stretched.
5. AI only for Brief extraction, style hints, and spec patches. AI never writes names/dates/official details or places text. Unknown stays null. Tool must work if AI fails.
6. Never fix names silently; show problems to the organizer.
7. Roles are config-driven (roles.json) and must differ in black and white.
8. QA checks run before showing any draft and after any change.
9. Same spec + same data = identical output.
10. Build phase by phase; never jump ahead. Developer knows basic Python: keep code simple and commented.

## Layout of the repo
- backend/ (FastAPI app, scripts, tests; run all Python commands from here)
- frontend/ (Next.js, built in Phase 6)
- assets/, sample_data/, output/ at the repo root

## Team ownership and git rules
- At the start of each session, read docs/TEAM.md and docs/OWNERS.json.
- Edit only files owned by the person you are helping (P1, P2, P3, or P4).
- Run `python scripts/check_ownership.py --owner <pN>` and `python -m pytest` before every push.
- If a change requires a file owned by someone else, STOP and ask the user to coordinate with that teammate rather than editing it directly.
