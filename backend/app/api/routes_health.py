"""Health check route."""
from fastapi import APIRouter

from app.config import APP_VERSION

router = APIRouter()


@router.get("/health")
@router.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}
