"""Export rendered cards to vector SVG/PDF or resolution-specific PNG."""

from __future__ import annotations

from io import BytesIO
from xml.etree import ElementTree

from typing import Any

from render import spec_adapter
from render.renderer import render_card

from export.settings import ExportSettings


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ElementTree.register_namespace("", SVG_NS)
ElementTree.register_namespace("xlink", XLINK_NS)


def export_card(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    settings: ExportSettings,
    *,
    layout: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
    canonical_spec: Any | None = None,
    canonical_person: Any | None = None,
) -> bytes:
    """Render and export one card in the requested format."""
    if canonical_spec is not None and canonical_person is not None:
        try:
            from app.render.svg_builder import build_svg
        except ImportError:
            from backend.app.render.svg_builder import build_svg
        svg = build_svg(canonical_spec, canonical_person)
    elif layout is not None and theme is not None:
        from render.renderer import _render
        svg = _render(spec, person, layout, theme)
    else:
        svg = render_card(spec, person)
    svg = _configure_svg(svg, spec, settings)
    if settings.format == "svg":
        return svg.encode("utf-8")

    if settings.format == "pdf":
        try:
            from app.export.pdf import svg_to_pdf_bytes
        except ImportError:
            from backend.app.export.pdf import svg_to_pdf_bytes
        return svg_to_pdf_bytes(svg)

    cairosvg = _load_cairosvg()
    if settings.format == "png":
        return cairosvg.svg2png(bytestring=svg.encode("utf-8"), dpi=settings.dpi)
    raise ValueError(f"Unsupported export format: {settings.format}")


def _configure_svg(
    svg: str,
    spec: spec_adapter.DesignSpec,
    settings: ExportSettings,
) -> str:
    """Set the trim/bleed viewport and optionally rotate the whole card."""
    canvas_width, canvas_height, trim_x, trim_y, trim_width, trim_height = (
        spec_adapter.canvas_geometry(spec)
    )
    if settings.bleed:
        origin_x, origin_y = 0.0, 0.0
        page_width, page_height = canvas_width, canvas_height
    else:
        origin_x, origin_y = trim_x, trim_y
        page_width, page_height = trim_width, trim_height

    root = ElementTree.fromstring(svg)
    if settings.orientation == "landscape":
        group = ElementTree.Element(
            f"{{{SVG_NS}}}g",
            {"transform": f"translate(0 {_number(origin_x + page_width)}) rotate(-90)"},
        )
        group.extend(list(root))
        root[:] = [group]
        root.set("width", f"{_number(page_height)}mm")
        root.set("height", f"{_number(page_width)}mm")
        root.set(
            "viewBox",
            f"{_number(origin_y)} 0 {_number(page_height)} {_number(page_width)}",
        )
    else:
        root.set("width", f"{_number(page_width)}mm")
        root.set("height", f"{_number(page_height)}mm")
        root.set(
            "viewBox",
            f"{_number(origin_x)} {_number(origin_y)} "
            f"{_number(page_width)} {_number(page_height)}",
        )
    return ElementTree.tostring(root, encoding="unicode")


def _load_cairosvg():
    """Load CairoSVG with the actionable Windows guidance used by Phase 1."""
    try:
        import cairosvg
    except (ImportError, OSError) as error:
        raise RuntimeError(
            "CairoSVG could not load its Cairo native library. Follow the Windows "
            f"install steps in README.md. Original error: {error}"
        ) from error
    return cairosvg


def _number(value: float) -> str:
    """Format an SVG measurement without unnecessary trailing zeroes."""
    return f"{value:g}"
