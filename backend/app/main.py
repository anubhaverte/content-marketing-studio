"""FastAPI app with automatic router discovery and error handlers.

Run from backend/ with: uvicorn app.main:app --reload
"""
import importlib
import pkgutil
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import api as api_pkg
from app.config import APP_VERSION
from app.refine.patch import PatchError
from app.spec.loader import SpecError

app = FastAPI(title="ID Card Studio", version=APP_VERSION)

# Allow the Next.js frontend to call this API during development and in production deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(SpecError)
async def spec_error_handler(_request: Request, exc: SpecError) -> JSONResponse:
    """Format SpecError as an HTTP 422 JSON response."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(PatchError)
async def patch_error_handler(_request: Request, exc: PatchError) -> JSONResponse:
    """Format PatchError as an HTTP 422 JSON response."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# Auto-discover every module in app.api whose name starts with "routes_" in sorted order
for module_info in sorted(pkgutil.iter_modules(api_pkg.__path__), key=lambda m: m.name):
    if module_info.name.startswith("routes_"):
        mod: Any = importlib.import_module(f"app.api.{module_info.name}")
        if hasattr(mod, "router"):
            app.include_router(mod.router)
