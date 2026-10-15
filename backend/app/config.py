"""Project paths and settings. All paths are built with pathlib, never hardcoded."""
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> parents[2] is the repo root
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
ASSETS = ROOT / "assets"
LOGOS = ASSETS / "logos"
FONTS = ASSETS / "fonts"
TEMPLATES = BACKEND / "app" / "templates"
LAYOUTS = TEMPLATES / "layouts"
THEMES = TEMPLATES / "themes"
OUTPUT = ROOT / "output"
SAMPLE_DATA = ROOT / "sample_data"

# Load backend/.env or root .env if it exists (holds GEMINI_API_KEY from Phase 5)
load_dotenv(BACKEND / ".env")
load_dotenv(ROOT / ".env")

APP_VERSION = "0.0.1"
