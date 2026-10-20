"""SVG -> PDF export (vector, exact physical size)."""
import base64
import io
import re
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path


def _resolve_asset_file(href: str) -> Path | None:
    """Find the actual file on disk for a relative or public path href."""
    href_clean = href.strip().split("?")[0].split("#")[0]
    if not href_clean or href_clean.startswith("data:"):
        return None

    clean = href_clean.lstrip("/")
    for prefix in (
        "frontend/public/logos/",
        "frontend/public/art/",
        "frontend/public/",
        "assets/logos/",
        "assets/art/",
        "assets/",
        "logos/",
        "art/",
    ):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
            break

    root_dir = Path(__file__).resolve().parent.parent.parent.parent
    search_dirs = [
        root_dir / "assets" / "logos",
        root_dir / "assets" / "art",
        root_dir / "assets",
        root_dir / "frontend" / "public" / "logos",
        root_dir / "frontend" / "public" / "art",
        root_dir / "frontend" / "public",
        Path.cwd() / "assets" / "logos",
        Path.cwd() / "assets" / "art",
        Path.cwd() / "assets",
    ]

    for base in (root_dir, Path.cwd()):
        direct = base / href_clean.lstrip("/")
        if direct.is_file():
            return direct

    for directory in search_dirs:
        cand = directory / clean
        if cand.is_file():
            return cand
        cand_name = directory / Path(clean).name
        if cand_name.is_file():
            return cand_name
    return None


def _prepare_svg_for_svglib(svg_text: str) -> str:
    """Preprocess SVG so that embedded SVG data URIs and external SVG/raster references

    in <image> tags are inlined as vector <g> or direct raster data URIs.
    This enables 100% rendering fidelity in ReportLab / svglib without Cairo.
    """
    image_pattern = re.compile(r'<image\b([^>]*)(?:/>|>(.*?)</image>)', re.DOTALL | re.IGNORECASE)

    def replace_image(match: re.Match) -> str:
        attrs_str = match.group(1)

        attr_dict = {}
        for attr_m in re.finditer(r'([a-zA-Z0-9_:-]+)\s*=\s*["\']([^"\']*)["\']', attrs_str):
            attr_dict[attr_m.group(1).lower()] = attr_m.group(2)

        href = (
            attr_dict.get("href")
            or attr_dict.get("{http://www.w3.org/1999/xlink}href")
            or attr_dict.get("xlink:href")
            or ""
        )
        if not href:
            return match.group(0)

        element_id = attr_dict.get("id", "elem")
        try:
            x = float(attr_dict.get("x", 0))
            y = float(attr_dict.get("y", 0))
            w = float(attr_dict.get("width", 0) or attr_dict.get("w", 0))
            h = float(attr_dict.get("height", 0) or attr_dict.get("h", 0))
        except ValueError:
            return match.group(0)

        opacity_attr = f' opacity="{attr_dict["opacity"]}"' if "opacity" in attr_dict else ""
        par = attr_dict.get("preserveaspectratio", "xMidYMid meet")

        svg_content = None

        # 1. Embedded SVG data URI
        if href.startswith("data:image/svg+xml"):
            parts = href.split(",", 1)
            if len(parts) == 2:
                payload = parts[1]
                if ";base64" in parts[0]:
                    try:
                        svg_content = base64.b64decode(payload).decode("utf-8", errors="replace")
                    except Exception:
                        svg_content = None
                else:
                    svg_content = urllib.parse.unquote(payload)

        # 2. File reference
        elif not href.startswith("data:"):
            resolved = _resolve_asset_file(href)
            if resolved and resolved.is_file():
                suffix = resolved.suffix.lower()
                if suffix == ".svg":
                    try:
                        svg_content = resolved.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        svg_content = None
                elif suffix in (".png", ".jpg", ".jpeg"):
                    mime = "image/png" if suffix == ".png" else "image/jpeg"
                    b64 = base64.b64encode(resolved.read_bytes()).decode("ascii")
                    new_href = f"data:{mime};base64,{b64}"
                    return f'<image id="{element_id}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}"{opacity_attr} preserveAspectRatio="{par}" href="{new_href}"/>'

        if not svg_content:
            return match.group(0)

        # Check if the SVG wraps an inner raster image (e.g. ACM logo!)
        raster_match = re.search(
            r'<image\b[^>]*(?:href|xlink:href)=["\'](data:image/(?:png|jpe?g);base64,[^"\']+)["\']',
            svg_content,
            re.IGNORECASE,
        )
        if raster_match:
            raster_uri = raster_match.group(1)
            return (
                f'<image id="{element_id}" x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}"'
                f'{opacity_attr} preserveAspectRatio="{par}" href="{raster_uri}"/>'
            )

        # Vector SVG: sanitize and inline as <g transform="...">
        try:
            cleaned_svg = re.sub(r'<\?xml[^>]*\?>', '', svg_content)
            cleaned_svg = re.sub(r'<!DOCTYPE[^>]*>', '', cleaned_svg)
            cleaned_svg = re.sub(r'xmlns(:\w+)?="[^"]*"', '', cleaned_svg)

            root = ET.fromstring(cleaned_svg.strip())
            vb = root.get("viewBox") or root.get("viewbox")
            if vb:
                vb_parts = [float(val) for val in vb.replace(",", " ").split() if val.strip()]
                if len(vb_parts) == 4:
                    min_x, min_y, vb_w, vb_h = vb_parts
                else:
                    min_x, min_y, vb_w, vb_h = 0, 0, w, h
            else:
                raw_w = "".join(c for c in root.get("width", str(w)) if c.isdigit() or c in ".-")
                raw_h = "".join(c for c in root.get("height", str(h)) if c.isdigit() or c in ".-")
                vb_w = float(raw_w) if raw_w else w
                vb_h = float(raw_h) if raw_h else h
                min_x, min_y = 0, 0

            if vb_w <= 0 or vb_h <= 0 or w <= 0 or h <= 0:
                return match.group(0)

            if "none" in par.lower():
                scale_x = w / vb_w
                scale_y = h / vb_h
                tx = x - min_x * scale_x
                ty = y - min_y * scale_y
                transform_str = f"translate({tx:.4f}, {ty:.4f}) scale({scale_x:.6f}, {scale_y:.6f})"
            elif "slice" in par.lower():
                scale = max(w / vb_w, h / vb_h)
                actual_w = vb_w * scale
                actual_h = vb_h * scale
                tx = x + (w - actual_w) / 2.0 - min_x * scale
                ty = y + (h - actual_h) / 2.0 - min_y * scale
                transform_str = f"translate({tx:.4f}, {ty:.4f}) scale({scale:.6f})"
            else:
                scale = min(w / vb_w, h / vb_h)
                actual_w = vb_w * scale
                actual_h = vb_h * scale
                tx = x + (w - actual_w) / 2.0 - min_x * scale
                ty = y + (h - actual_h) / 2.0 - min_y * scale
                transform_str = f"translate({tx:.4f}, {ty:.4f}) scale({scale:.6f})"

            inner_match = re.search(r'<svg[^>]*>(.*)</svg>', cleaned_svg, re.DOTALL | re.IGNORECASE)
            inner_body = inner_match.group(1) if inner_match else "".join(ET.tostring(child, encoding="unicode") for child in root)

            return f'<g id="{element_id}"{opacity_attr} transform="{transform_str}">{inner_body}</g>'
        except Exception:
            return match.group(0)

    return image_pattern.sub(replace_image, svg_text)


def svg_to_pdf_bytes(svg_text: str) -> bytes:
    """Convert SVG text to vector PDF bytes, using CairoSVG with ReportLab fallback."""
    try:
        import cairosvg
        return cairosvg.svg2pdf(bytestring=svg_text.encode("utf-8"))
    except Exception:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF

        clean_svg = _prepare_svg_for_svglib(svg_text)
        drawing = svg2rlg(io.StringIO(clean_svg))
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


