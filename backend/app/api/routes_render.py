"""Render routes for card preview and batch generation."""
from __future__ import annotations

import base64
import io
import json
import re
import sys
import zipfile
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

from app.api.models import RenderPreviewRequest, RenderPreviewResponse
from app.api.render_models import (
    RenderBatchRequest,
    RenderBatchResponse,
    RenderPrintSheetRequest,
)
from app.config import LAYOUTS, ROOT
from app.export.print_sheet import make_print_sheet
from app.render.svg_builder import build_svg
from app.spec.loader import SpecError, load_layout as load_spec_layout
from app.spec.schema import (
    CircleEl,
    GradientFill,
    LineEl,
    LogoEl,
    PhotoEl,
    QrEl,
    RectEl,
    RoleBadgeEl,
    SvgAssetEl,
    TextEl,
)

# Ensure repository root is in sys.path for render and qa modules
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from export.batch import export_batch, export_batch_pdf
from export.settings import ExportSettings
from qa.checks import run_qa
from qa.report import issues_to_dict
from render import spec_adapter
from render.loaders import load_layout
from render.renderer import _render

router = APIRouter(prefix="/render", tags=["render"])

DEFAULT_FALLBACK_ROLES = {
    "participant": "#1F6FEB",
    "organizer": "#D9480F",
    "mentor": "#2F9E44",
    "volunteer": "#7E22CE",
}


def _adapt_theme_dict(spec: Any) -> dict[str, Any]:
    """Convert a canonical DesignSpec's theme model to renderer theme format."""
    theme_model = spec.theme
    colors_model = theme_model.colors

    # Text on primary color with fallback
    text_on_primary = getattr(colors_model, "text_on_primary", None) or "#FFFFFF"

    # Fonts fallback list
    heading_font = theme_model.fonts.heading
    body_font = theme_model.fonts.body
    fonts_dict = {
        "heading": [heading_font, "Arial", "Segoe UI"] if isinstance(heading_font, str) else list(heading_font),
        "body": [body_font, "Arial", "sans-serif"] if isinstance(body_font, str) else list(body_font),
    }

    # Role colors ensuring all 4 standard roles exist
    role_colors = dict(theme_model.role_colors)
    for role, default_col in DEFAULT_FALLBACK_ROLES.items():
        if role not in role_colors or not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(role_colors[role])):
            role_colors[role] = default_col

    # Ensure roles have distinct colors
    assigned_colors = list(role_colors.values())
    if len(set(assigned_colors)) != len(assigned_colors):
        used: set[str] = set()
        for role in spec_adapter.ROLES:
            col = role_colors.get(role, DEFAULT_FALLBACK_ROLES[role])
            if col in used:
                col = DEFAULT_FALLBACK_ROLES[role]
            used.add(col)
            role_colors[role] = col

    colors_dict = {
        "primary": colors_model.primary,
        "secondary": colors_model.secondary,
        "background": colors_model.background,
        "accent": colors_model.accent,
        "text": colors_model.text,
        "text_on_primary": text_on_primary,
    }

    from render.photo import _contrast_ratio

    # Ensure each role color meets the mandatory 4.5:1 contrast requirement
    for role, col in list(role_colors.items()):
        ratio_top = _contrast_ratio(col, colors_dict["text_on_primary"])
        ratio_text = _contrast_ratio(col, colors_dict["text"])
        if max(ratio_top, ratio_text) < 4.5:
            if col == "#D9480F":
                role_colors[role] = "#C2410C"
            elif _contrast_ratio(col, "#000000") >= 4.5:
                colors_dict["text"] = "#000000"

    return {
        "name": theme_model.name,
        "colors": colors_dict,
        "role_colors": role_colors,
        "fonts": fonts_dict,
        "_source_file": f"theme {theme_model.name}",
    }



def _adapt_spec(spec: Any) -> spec_adapter.DesignSpec:
    """Convert a canonical DesignSpec to spec_adapter.DesignSpec."""
    logos = set()
    if spec.brand and spec.brand.logos:
        for k in spec.brand.logos.keys():
            k_lower = k.lower()
            if "acm" in k_lower:
                logos.add("acm")
            if "svnit" in k_lower:
                logos.add("svnit")
            logos.add(k)
    else:
        logos = {"acm", "svnit"}

    return spec_adapter.DesignSpec({
        "layout": spec.layout_name.lower(),
        "theme": spec.theme_name.lower(),
        "card": {
            "width_mm": spec.page.width_mm,
            "height_mm": spec.page.height_mm,
            "bleed_mm": spec.page.bleed_mm,
            "safe_mm": spec.page.safe_mm,
        },
        "event": {
            "name": spec.event.event_name,
            "tagline": spec.event.tagline,
            "venue": spec.event.venue,
            "date": spec.event.dates,
        },
        "logos": sorted(logos),
        "attendance_url_base": None,
    })


def _adapt_person(person: Any) -> spec_adapter.Person:
    """Convert a canonical Person to spec_adapter.Person."""
    extra = getattr(person, "extra", {}) or {}

    raw_photo = getattr(person, "photo", None) or extra.get("photo")
    if isinstance(raw_photo, str):
        cleaned_photo = raw_photo.strip().replace("\\", "/")
        if cleaned_photo.startswith("sample_data/"):
            cleaned_photo = cleaned_photo[len("sample_data/"):]
    else:
        cleaned_photo = None

    raw_id = getattr(person, "id", None) or extra.get("id")
    raw_team = getattr(person, "team", None) or extra.get("team")
    raw_email = getattr(person, "email", None) or extra.get("email")
    raw_qr = getattr(person, "qr_url", None) or extra.get("qr_url")

    data = {
        "name": getattr(person, "name", ""),
        "role": getattr(person, "role", "participant"),
        "id": raw_id,
        "photo": cleaned_photo,
        "team": raw_team,
        "email": raw_email,
        "qr_url": raw_qr,
    }
    source_file = str(ROOT / "sample_data" / "people.json")
    return spec_adapter.Person(data, _source_file=source_file)



@router.post("/preview", response_model=RenderPreviewResponse)
def render_preview(payload: Optional[RenderPreviewRequest] = None) -> Any:
    """Render a live SVG card preview from a DesignSpec and Person.

    Returns the complete SVG markup and automatic QA evaluation.
    Preserves 501 status for empty legacy calls.
    """
    if payload is None:
        return JSONResponse(status_code=501, content={"detail": "Not implemented yet. Built in Phase 2."})

    spec = payload.spec
    person = payload.person

    # Confirm the selected template still exists; the merged DesignSpec carries
    # the editable elements used for rendering.
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", spec.layout_name):
        raise HTTPException(
            status_code=422,
            detail=f"Layout '{spec.layout_name}' cannot be loaded: invalid layout name",
        )
    try:
        layout = load_spec_layout(LAYOUTS / f"{spec.layout_name}.json")
    except SpecError as err:
        raise HTTPException(
            status_code=422,
            detail=f"Layout '{spec.layout_name}' cannot be loaded: {err}",
        ) from err
    if layout.name != spec.layout_name:
        raise HTTPException(status_code=422, detail="Loaded layout name does not match the DesignSpec")

    try:
        svg = build_svg(spec, person, debug_guides=payload.debug_guides)
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Rendering failed: {err}",
        ) from err

    qa_issues = run_qa(
        _adapt_spec(spec),
        _adapt_person(person),
        svg,
        _qa_layout(spec, svg),
        _qa_theme(spec),
    )
    issues_list = issues_to_dict(qa_issues)
    if person.role not in spec.theme.role_colors:
        issues_list.append({
            "check": "role_configuration",
            "severity": "warning",
            "person_id": person.id,
            "message": f"Role {person.role!r} has no theme role color; the primary color is used.",
        })

    return RenderPreviewResponse(
        svg=svg,
        qa_issues=issues_list,
    )


def _qa_layout(spec: Any, svg: str) -> dict[str, Any]:
    """Adapt canonical elements to the established QA checker geometry."""
    from xml.etree import ElementTree

    root = ElementTree.fromstring(svg)
    rendered_by_id = {
        node.get("id"): node
        for node in root.iter()
        if node.get("id") is not None
    }
    elements = []
    for index, element in enumerate(spec.elements):
        element_id = element.id or f"{element.type}-{index}"
        item: dict[str, Any] = {
            "id": element_id,
            "type": element.type,
        }
        if isinstance(element, RectEl):
            item.update(_qa_box(element.x, element.y, element.w, element.h))
            item["color"] = element.fill if isinstance(element.fill, str) else "background"
            item["role_area"] = element.fill == "role"
            item["background_only"] = True
            if isinstance(element.fill, GradientFill):
                item["color"] = element.fill.stops[0][1]
        elif isinstance(element, TextEl):
            line_height = element.max_font * 0.352778 * 1.2
            box_height = line_height * element.max_lines
            x = {
                "left": element.x,
                "center": element.x + element.w / 2,
                "right": element.x + element.w,
            }[element.align]
            item.update(_qa_box(x, element.y + box_height / 2, element.w, box_height))
            item.update({
                "data": f"person.{element.field}" if element.field else element.value,
                "max_width": element.w,
                "alignment": {"left": "start", "center": "middle", "right": "end"}[element.align],
                "color": element.color,
            })
        elif isinstance(element, LogoEl):
            node = rendered_by_id.get(element_id)
            x, y = float(node.get("x", element.x)), float(node.get("y", element.y))
            width = float(node.get("width", element.w))
            height = float(node.get("height", element.h or element.w))
            item.update(_qa_box(x, y, width, height))
            item["data"] = element.src
        elif isinstance(element, (PhotoEl, RoleBadgeEl, QrEl, SvgAssetEl)):
            item.update(_qa_box(element.x, element.y, element.w, element.h))
            if isinstance(element, PhotoEl):
                item["color"] = "secondary"
                item["data"] = f"person.{element.field}"
            elif isinstance(element, RoleBadgeEl):
                item["data"] = f"person.{element.field}"
            elif isinstance(element, QrEl):
                item["data"] = f"person.{element.field}"
        elif isinstance(element, LineEl):
            item.update(_qa_box(
                min(element.x1, element.x2),
                min(element.y1, element.y2),
                abs(element.x2 - element.x1),
                abs(element.y2 - element.y1),
            ))
        elif isinstance(element, CircleEl):
            item.update(_qa_box(
                element.cx - element.r,
                element.cy - element.r,
                element.r * 2,
                element.r * 2,
            ))
        elements.append(item)
    return {"elements": elements}


def _qa_box(x: float, y: float, width: float, height: float) -> dict[str, Any]:
    return {
        "position": {"x": x, "y": y},
        "size": {"width": width, "height": height},
    }


def _qa_theme(spec: Any) -> dict[str, Any]:
    """Adapt theme tokens without inventing colors for QA."""
    colors = spec.theme.colors.model_dump()
    colors["text_on_primary"] = "#FFFFFF"
    return {
        "colors": colors,
        "role_colors": dict(spec.theme.role_colors),
        "fonts": {
            "heading": [spec.theme.fonts.heading],
            "body": [spec.theme.fonts.body],
        },
    }


@router.post("/batch")
def render_batch(payload: Optional[RenderBatchRequest] = None) -> Any:
    """Render and export a batch of ID cards.

    Supports ZIP packaging of individual cards (with QA report) or collated multi-page PDF.
    Preserves 501 status for legacy parameterless calls.
    """
    if payload is None:
        return JSONResponse(status_code=501, content={"detail": "Not implemented yet. Built in Phase 3."})

    spec = payload.spec
    people = payload.people

    # Bounded processing checks
    if len(people) == 0:
        raise HTTPException(status_code=400, detail="Batch attendees list cannot be empty.")
    if len(people) > 500:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(people)} exceeds the maximum limit of 500.",
        )

    # 1. Load layout
    try:
        layout_dict = load_layout(spec.layout_name.lower())
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Layout '{spec.layout_name}' cannot be loaded: {err}",
        )

    # 2. Adapt theme, spec, and people
    try:
        theme_dict = _adapt_theme_dict(spec)
        spec_adapted = _adapt_spec(spec)
        people_adapted = [_adapt_person(p) for p in people]
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Specification or attendee adaptation failed: {err}",
        )

    # 3. Resolve export settings
    if payload.settings:
        card_format = payload.settings.format
        dpi = payload.settings.dpi
        orientation = payload.settings.orientation
        bleed = payload.settings.bleed
    else:
        # Fallback to top-level format or defaults
        req_fmt = payload.format or "pdf"
        card_format = "pdf" if req_fmt == "zip" else req_fmt
        dpi = 300
        orientation = "portrait"
        bleed = True

    try:
        export_settings = ExportSettings(
            format=card_format,
            dpi=dpi,
            orientation=orientation,
            bleed=bleed,
        )
    except Exception as err:
        raise HTTPException(status_code=422, detail=f"Invalid export settings: {err}")

    # 4. Generate batch output
    if payload.collate_pdf:
        if export_settings.format != "pdf":
            raise HTTPException(
                status_code=400,
                detail="Multi-page collation is only supported for PDF format.",
            )
        try:
            pdf_bytes = export_batch_pdf(
                spec_adapted,
                people_adapted,
                export_settings,
                layout=layout_dict,
                theme=theme_dict,
                canonical_spec=spec,
                canonical_people=people,
            )
        except Exception as err:
            raise HTTPException(
                status_code=422,
                detail=f"Batch PDF collation failed: {err}",
            )

        if payload.return_json:
            return RenderBatchResponse(
                totals={
                    "people": len(people),
                    "exported": len(people),
                    "failed": 0,
                    "skipped_rows": len(payload.skipped_rows),
                    "qa_issues": 0,
                },
                people=[{"id": p.id or p.get_field("id"), "status": "exported"} for p in people],
                skipped_rows=list(payload.skipped_rows),
                settings=export_settings.to_dict(),
                archive_base64=base64.b64encode(pdf_bytes).decode("ascii"),
                filename="cards.pdf",
                media_type="application/pdf",
            )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="cards.pdf"',
                "X-Total-Count": str(len(people)),
                "X-Exported-Count": str(len(people)),
                "X-Failed-Count": "0",
            },
        )

    # ZIP packaging (default)
    try:
        archive_bytes = export_batch(
            spec_adapted,
            people_adapted,
            export_settings,
            skipped_rows=payload.skipped_rows,
            layout=layout_dict,
            theme=theme_dict,
            canonical_spec=spec,
            canonical_people=people,
        )
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Batch export failed: {err}",
        )

    # Parse report from zip for metadata headers and/or JSON response
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
        report_data = json.loads(z.read("report.json").decode("utf-8"))

    totals = report_data.get("totals", {})

    if payload.return_json:
        return RenderBatchResponse(
            totals=totals,
            people=report_data.get("people", []),
            skipped_rows=report_data.get("skipped_rows", []),
            settings=report_data.get("settings", export_settings.to_dict()),
            archive_base64=base64.b64encode(archive_bytes).decode("ascii"),
            filename="cards.zip",
            media_type="application/zip",
        )

    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="cards.zip"',
            "X-Total-Count": str(totals.get("people", len(people))),
            "X-Exported-Count": str(totals.get("exported", 0)),
            "X-Failed-Count": str(totals.get("failed", 0)),
            "X-QA-Issue-Count": str(totals.get("qa_issues", 0)),
        },
    )


@router.post("/print-sheet", operation_id="render_print_sheet")
@router.post("/print_sheet", operation_id="render_print_sheet_alias")
def render_print_sheet(payload: RenderPrintSheetRequest) -> Response:
    """Generate and return an imposed A4/A3 print sheet PDF with crop marks."""
    import tempfile
    from pathlib import Path

    if not payload.people:
        raise HTTPException(status_code=400, detail="Print sheet attendees list cannot be empty.")
    if len(payload.people) > 500:
        raise HTTPException(status_code=400, detail=f"Batch size {len(payload.people)} exceeds the limit of 500.")

    # Render card SVGs for all attendees
    card_svgs: list[str] = []
    for person in payload.people:
        try:
            svg = build_svg(payload.spec, person)
            card_svgs.append(svg)
        except Exception as err:
            raise HTTPException(status_code=422, detail=f"Failed rendering card for {person.name}: {err}") from err

    # Create print sheet in a temporary file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        make_print_sheet(
            card_svgs=card_svgs,
            out_path=tmp_path,
            page=payload.page,
            crop_marks=payload.crop_marks,
        )
        pdf_bytes = tmp_path.read_bytes()
    except Exception as err:
        raise HTTPException(status_code=422, detail=f"Failed creating print sheet: {err}") from err
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # Calculate total pages: A4 is 3x3=9 cards/page, A3 is 4x4=16 cards/page
    cards_per_page = 9 if payload.page == "A4" else 16
    total_pages = (len(payload.people) + cards_per_page - 1) // cards_per_page

    filename = f"print_sheet_{payload.page.lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Total-Count": str(len(payload.people)),
            "X-Total-Cards": str(len(payload.people)),
            "X-Total-Pages": str(total_pages),
            "X-Page-Format": payload.page,
        },
    )


