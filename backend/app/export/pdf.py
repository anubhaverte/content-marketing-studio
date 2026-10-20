"""SVG -> PDF export (vector, exact physical size)."""
import io
from pathlib import Path


def svg_to_pdf_bytes(svg_text: str) -> bytes:
    """Convert SVG text to vector PDF bytes, using CairoSVG with ReportLab fallback."""
    try:
        import cairosvg
        return cairosvg.svg2pdf(bytestring=svg_text.encode("utf-8"))
    except Exception:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF

        drawing = svg2rlg(io.StringIO(svg_text))
        if drawing is None:
            raise ValueError("Could not parse SVG markup into ReportLab drawing.")
        buf = io.BytesIO()
        renderPDF.drawToFile(drawing, buf)
        return buf.getvalue()


def svg_to_pdf(svg_text: str, out_path: Path) -> Path:
    """Convert SVG text to a vector PDF. The page size comes from the SVG's width/height in mm."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = svg_to_pdf_bytes(svg_text)
    out_path.write_bytes(pdf_bytes)
    return out_path

