"""Project paths and settings. All paths are built with pathlib, never hardcoded."""
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> parents[2] is repo root when run from repo, parents[1] if backend is service root
_file_path = Path(__file__).resolve()
if len(_file_path.parents) > 2 and (_file_path.parents[2] / "backend").exists():
    ROOT = _file_path.parents[2]
    BACKEND = ROOT / "backend"
elif len(_file_path.parents) > 1 and (_file_path.parents[1] / "app").exists():
    ROOT = _file_path.parents[1]
    BACKEND = ROOT
else:
    ROOT = _file_path.parents[1]
    BACKEND = ROOT

ASSETS = (ROOT / "assets") if (ROOT / "assets").exists() else (BACKEND / "app" / "assets")
LOGOS = (ASSETS / "logos") if (ASSETS / "logos").exists() else (BACKEND / "app" / "assets" / "logos")
FONTS = (ASSETS / "fonts") if (ASSETS / "fonts").exists() else (BACKEND / "app" / "assets" / "fonts")
TEMPLATES = BACKEND / "app" / "templates"
LAYOUTS = TEMPLATES / "layouts"
THEMES = TEMPLATES / "themes"
OUTPUT = ROOT / "output"
SAMPLE_DATA = (ROOT / "sample_data") if (ROOT / "sample_data").exists() else (BACKEND / "sample_data")

# Load backend/.env or root .env if it exists (holds GEMINI_API_KEY from Phase 5)
load_dotenv(BACKEND / ".env")
load_dotenv(ROOT / ".env")

APP_VERSION = "0.0.1"

