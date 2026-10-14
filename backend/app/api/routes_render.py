"""Render routes. Stubs for now: they return 501 until the named phase."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/render")


@router.post("/preview")
def render_preview() -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": "Not implemented yet. Built in Phase 2."})


@router.post("/batch")
def render_batch() -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": "Not implemented yet. Built in Phase 3."})
