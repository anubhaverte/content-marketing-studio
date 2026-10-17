"""Export routes providing /export prefix endpoints.

Owned by Person 2 per docs/OWNERS.json.
"""
from fastapi import APIRouter, Response

from app.api.render_models import RenderPrintSheetRequest
from app.api.routes_render import render_print_sheet

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/print-sheet", operation_id="export_print_sheet")
@router.post("/print_sheet", operation_id="export_print_sheet_alias")
def export_print_sheet(payload: RenderPrintSheetRequest) -> Response:
    """Generate and return an imposed A4/A3 print sheet PDF via /export prefix."""
    return render_print_sheet(payload)
