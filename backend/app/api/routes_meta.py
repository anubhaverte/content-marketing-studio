"""Metadata and schema reflection routes."""
import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.brief.schema import Brief
from app.config import TEMPLATES
from app.spec.schema import DesignSpec, Layout, PatchOp, Person, Theme

router = APIRouter(tags=["meta"])

SCHEMA_MAP: dict[str, Any] = {
    "layout": Layout,
    "theme": Theme,
    "design-spec": DesignSpec,
    "design_spec": DesignSpec,
    "brief": Brief,
    "person": Person,
    "patch-op": PatchOp,
    "patch_op": PatchOp,
}


@router.get("/roles")
def get_roles() -> list[dict[str, Any]]:
    """Return the configured roles from templates/roles.json."""
    roles_path = TEMPLATES / "roles.json"
    if not roles_path.exists():
        raise HTTPException(status_code=404, detail="roles.json not found")
    try:
        return json.loads(roles_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Corrupted roles.json: {exc}") from exc


@router.get("/schema/{name}")
def get_schema(name: str) -> dict[str, Any]:
    """Return the JSON Schema for a core specification model."""
    model_cls = SCHEMA_MAP.get(name)
    if model_cls is None:
        valid_schemas = ", ".join(sorted(SCHEMA_MAP.keys()))
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{name}' not found. Valid schemas: {valid_schemas}",
        )
    return model_cls.model_json_schema()
