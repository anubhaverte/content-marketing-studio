# Conventions

- **Units:** millimeters everywhere. Origin (0,0) is the TOP-LEFT of the 60 x 92 mm canvas (trim + bleed), not the trim line.
- **Fonts:** sizes in JSON are points (pt). Convert with 1 pt = 0.352778 mm when writing SVG.
- **Colors:** layouts use theme tokens (`background`, `primary`, `secondary`, `accent`, `text`), never hex. Themes use hex.
- **Models:** every Pydantic model uses `extra="forbid"` so typos are errors.
- **Code style:** type hints and a short docstring on every function. Simple, readable code with comments. Use `pathlib` for paths and never hardcode absolute paths.
- **Logging:** use the `logging` module in library code, not `print` (scripts may print).
- **Determinism:** same spec + same data = identical output. Random generators use fixed seeds.
- **Stubs:** unfinished functions raise `NotImplementedError("Phase N: ...")` naming the phase that implements them.
- **Images:** embedded in SVG as data URIs (`app/render/embed.py`), never linked by file path.
- **AI:** never writes names, dates or official details, never places text. Unknown values stay `None` and become follow-up questions.
- **QA:** runs after any spec change, including AI-driven ones.
- **Git:** `main` always works. Branch per task (`feature/<thing>`), small commits, pull requests.
