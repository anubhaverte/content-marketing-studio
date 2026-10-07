"""FastAPI app. Run from backend/ with: uvicorn app.main:app --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_health, routes_render
from app.config import APP_VERSION

app = FastAPI(title="ID Card Studio", version=APP_VERSION)

# Allow the Next.js frontend (Phase 6) to call this API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_health.router)
app.include_router(routes_render.router)
