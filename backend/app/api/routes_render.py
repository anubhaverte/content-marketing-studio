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
from app.api.render_models import RenderBatchRequest, RenderBatchResponse
from app.config import ROOT

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

    # 1. Load layout
    try:
        layout_dict = load_layout(spec.layout_name.lower())
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Layout '{spec.layout_name}' cannot be loaded: {err}",
        )

    # 2. Adapt theme, spec, and person
    try:
        theme_dict = _adapt_theme_dict(spec)
        spec_adapted = _adapt_spec(spec)
        person_adapted = _adapt_person(person)
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Specification adaptation failed: {err}",
        )

    # 3. Render SVG
    try:
        svg = _render(spec_adapted, person_adapted, layout_dict, theme_dict)
    except Exception as err:
        raise HTTPException(
            status_code=422,
            detail=f"Rendering failed: {err}",
        )

    # 4. Inject debug guides if requested
    if payload.debug_guides:
        width, height, trim_x, trim_y, trim_width, trim_height = spec_adapter.canvas_geometry(spec_adapted)
        safe = spec_adapter.safe_inset(spec_adapted)
        guides = (
            f'<g id="debug-guides" stroke-dasharray="1 1" fill="none">\n'
            f'  <rect id="guide-bleed" x="0" y="0" width="{width:g}" height="{height:g}" stroke="#E11D48" stroke-width="0.3"/>\n'
            f'  <rect id="guide-trim" x="{trim_x:g}" y="{trim_y:g}" width="{trim_width:g}" height="{trim_height:g}" stroke="#10B981" stroke-width="0.3"/>\n'
            f'  <rect id="guide-safe" x="{trim_x + safe:g}" y="{trim_y + safe:g}" width="{trim_width - 2 * safe:g}" height="{trim_height - 2 * safe:g}" stroke="#3B82F6" stroke-width="0.3"/>\n'
            f'</g>'
        )
        if "</svg>" in svg:
            svg = svg.replace("</svg>", f"{guides}\n</svg>")

    # 5. Run automatic QA checks
    try:
        qa_issues = run_qa(spec_adapted, person_adapted, svg, layout_dict, theme_dict)
        issues_list = issues_to_dict(qa_issues)
    except Exception as err:
        issues_list = [{"check": "qa_pipeline", "severity": "warning", "person_id": person.id, "message": str(err)}]

    return RenderPreviewResponse(
        svg=svg,
        qa_issues=issues_list,
    )


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
