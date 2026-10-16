"""Check that this computer is ready to run the project.

Run from backend/:  python scripts/check_env.py
Prints PASS / FAIL for each check. INFO lines never cause a failure.
"""
import importlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

results = []  # (status, label, detail)


def record(status: str, label: str, detail: str = "") -> None:
    results.append((status, label, detail))


# 1. Python version
v = sys.version_info
record("PASS" if v >= (3, 10) else "FAIL", "Python 3.10+", f"{v.major}.{v.minor}.{v.micro}")

# 2. Required packages
PACKAGES = ["fastapi", "uvicorn", "pydantic", "jinja2", "cairosvg", "PIL", "pandas", "segno",
            "cv2", "multipart", "pypdf", "reportlab", "dotenv", "pytest", "httpx"]
for pkg in PACKAGES:
    try:
        importlib.import_module(pkg)
        record("PASS", f"import {pkg}")
    except Exception as e:  # noqa: BLE001 - we want to report any import problem
        record("FAIL", f"import {pkg}", str(e).splitlines()[0][:80])

# 3. CairoSVG can render
try:
    import cairosvg

    tiny = '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="10mm"><rect width="10" height="10" fill="red"/></svg>'
    png = cairosvg.svg2png(bytestring=tiny.encode())
    record("PASS" if png[:4] == b"\x89PNG" else "FAIL", "CairoSVG renders a PNG")
except Exception as e:  # noqa: BLE001
    record("FAIL", "CairoSVG renders a PNG", str(e).splitlines()[0][:80] + "  (Cairo library missing? see README)")

# 4-7. Project files
try:
    from app.config import LOGOS, OUTPUT, LAYOUTS, THEMES, TEMPLATES
    from app.spec.loader import SpecError, load_layout, load_theme

    OUTPUT.mkdir(exist_ok=True)
    probe = OUTPUT / ".write_test"
    try:
        probe.write_text("ok")
        probe.unlink()
        record("PASS", "output/ folder is writable")
    except OSError as e:
        record("FAIL", "output/ folder is writable", str(e))

    for logo in ("acm_nitsurat.svg", "svnit.svg"):
        record("PASS" if (LOGOS / logo).exists() else "FAIL", f"logo file {logo}")

    try:
        load_layout(LAYOUTS / "classic.json")
        record("PASS", "starter layout classic.json is valid")
    except SpecError as e:
        record("FAIL", "starter layout classic.json is valid", str(e).splitlines()[0])
    try:
        load_theme(THEMES / "clean_light.json")
        record("PASS", "starter theme clean_light.json is valid")
    except SpecError as e:
        record("FAIL", "starter theme clean_light.json is valid", str(e).splitlines()[0])
    try:
        roles = json.loads((TEMPLATES / "roles.json").read_text(encoding="utf-8"))
        record("PASS", "roles.json loads", ", ".join(r["id"] for r in roles))
    except Exception as e:  # noqa: BLE001
        record("FAIL", "roles.json loads", str(e))
except Exception as e:  # noqa: BLE001
    record("FAIL", "project modules import", str(e))

# 8. Fonts (INFO only)
try:
    out = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=10).stdout.lower()
    for font in ("poppins", "inter"):
        record("INFO", f"font {font.title()} visible to system", "yes" if font in out else "no (real fonts are set up in Phase 1)")
except Exception:  # noqa: BLE001
    record("INFO", "font check", "could not list system fonts (fc-list not available); real fonts are set up in Phase 1")

width = max(len(r[1]) for r in results)
for status, label, detail in results:
    print(f"[{status:4}] {label.ljust(width)}  {detail}")

failed = [r for r in results if r[0] == "FAIL"]
print(f"\n{len(failed)} failed, {sum(1 for r in results if r[0] == 'PASS')} passed")
sys.exit(1 if failed else 0)
