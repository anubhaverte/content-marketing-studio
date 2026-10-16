"""Template listing and retrieval routes."""
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from app.generator.library import get_layout, get_theme, list_layouts, list_themes
from app.spec.loader import SpecError
from app.spec.schema import Layout, Theme

router = APIRouter(prefix="/templates", tags=["templates"])

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@router.get("/layouts")
def get_layouts() -> list[str]:
    """Return the list of available layout names."""
    return list_layouts()


@router.get("/themes")
def get_themes() -> list[str]:
    """Return the list of available theme names."""
    return list_themes()


@router.get("/layouts/{name}", response_model=Layout)
def get_layout_by_name(name: str) -> Any:
    """Return validated JSON for a layout by name."""
    if not NAME_PATTERN.match(name):
        raise HTTPException(status_code=422, detail=f"Invalid layout name format: '{name}'")
    try:
        return get_layout(name)
    except SpecError as exc:
        raise HTTPException(status_code=404, detail=f"Layout '{name}' not found") from exc


@router.get("/themes/{name}", response_model=Theme)
def get_theme_by_name(name: str) -> Any:
    """Return validated JSON for a theme by name."""
    if not NAME_PATTERN.match(name):
        raise HTTPException(status_code=422, detail=f"Invalid theme name format: '{name}'")
    try:
        return get_theme(name)
    except SpecError as exc:
        raise HTTPException(status_code=404, detail=f"Theme '{name}' not found") from exc
