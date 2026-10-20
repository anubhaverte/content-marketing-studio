"""Build deterministic SVG cards from a merged DesignSpec and one person."""

from __future__ import annotations

import base64
import json
import warnings
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from app.config import SAMPLE_DATA, TEMPLATES
from app.render.elements import (
    draw_circle,
    draw_line,
    draw_logo,
    draw_photo,
    draw_qr,
    draw_rect,
    draw_role_badge,
    draw_svg_asset,
    draw_text,
)
from app.render.embed import file_to_data_uri
from app.spec.paths import asset_path
from app.spec.schema import (
    CircleEl,
    DesignSpec,
    LineEl,
    LogoEl,
    Person,
    PhotoEl,
    QrEl,
    RectEl,
    RoleBadgeEl,
    SvgAssetEl,
    TextEl,
)


def build_svg(spec: DesignSpec, person: Person, debug_guides: bool = False) -> str:
    """Draw layout elements from back to front and return a self-contained SVG."""
    used_logos = {element.src for element in spec.elements if isinstance(element, LogoEl)}
    normalized_used = set()
    for l in used_logos:
        if l in ("acm", "acm_nitsurat", "logo_acm"):
            normalized_used.add("acm_nitsurat")
        if l in ("svnit", "logo_svnit"):
            normalized_used.add("svnit")
        normalized_used.add(l)
    required_logos = {"acm_nitsurat", "svnit"}
    missing_logos = required_logos - normalized_used
    if missing_logos:
        raise ValueError(f"Layout is missing required logos: {', '.join(sorted(missing_logos))}")

    role = person.role
    font_faces: dict[tuple[str, str], Path] = {}
    fragments: list[str] = []
    for index, element in enumerate(spec.elements):
        element_id = element.id or f"{element.type}-{index}"
        if isinstance(element, RectEl):
            fragments.append(draw_rect(element, spec.theme, role, element_id))
        elif isinstance(element, LineEl):
            fragments.append(draw_line(element, spec.theme, role, element_id))
        elif isinstance(element, CircleEl):
            fragments.append(draw_circle(element, spec.theme, role, element_id))
        elif isinstance(element, TextEl):
            value = element.value
            if value is None and element.field:
                value = person.get_field(element.field)
                if value is None:
                    if element.field in ("event_name", "event.name", "event"):
                        value = getattr(spec.event, "event_name", None) or "EVENT NAME"
                    elif element.field in ("tagline", "event.tagline"):
                        value = getattr(spec.event, "tagline", None)
                    elif element.field in ("venue", "event.venue"):
                        value = getattr(spec.event, "venue", None)
                    elif element.field in ("dates", "date", "event.dates", "event.date"):
                        value = getattr(spec.event, "dates", None)
            if value:
                fragments.append(draw_text(element, spec.theme, value, role, element_id, font_faces))
        elif isinstance(element, PhotoEl):
            photo_uri = _photo_data_uri(person, element)
            fragments.append(
                draw_photo(
                    element,
                    photo_uri,
                    _initials(person.name),
                    spec.theme,
                    element_id,
                    font_faces,
                )
            )
        elif isinstance(element, LogoEl):
            try:
                uri = None
                aspect_ratio = 1.0
                rel_path = spec.brand.logos.get(element.src) if spec.brand and spec.brand.logos else None
                if rel_path and rel_path.startswith("data:"):
                    uri = rel_path
                    try:
                        if "image/svg+xml" in uri:
                            parts = uri.split(",", 1)
                            if len(parts) == 2:
                                import urllib.parse
                                raw_svg = base64.b64decode(parts[1]).decode("utf-8", errors="replace") if ";base64" in parts[0] else urllib.parse.unquote(parts[1])
                                r_el = ElementTree.fromstring(raw_svg)
                                vb = r_el.get("viewBox") or r_el.get("viewbox")
                                if vb:
                                    vbs = [float(v) for v in vb.replace(",", " ").split()]
                                    if len(vbs) == 4 and vbs[3] > 0:
                                        aspect_ratio = vbs[2] / vbs[3]
                        else:
                            from PIL import Image
                            import io
                            parts = uri.split(",", 1)
                            if len(parts) == 2:
                                im = Image.open(io.BytesIO(base64.b64decode(parts[1])))
                                if im.size[1] > 0:
                                    aspect_ratio = im.size[0] / im.size[1]
                    except Exception:
                        aspect_ratio = 1.0
                else:
                    path = _logo_path(spec, element)
                    uri = file_to_data_uri(path)
                    aspect_ratio = _asset_aspect_ratio(path)

                fragments.append(
                    draw_logo(
                        element,
                        uri,
                        aspect_ratio,
                        element_id,
                        element.src,
                    )
                )
            except (FileNotFoundError, ValueError) as err:
                # Essential organization logos must exist (Rule 4)
                if element.src in ("acm", "svnit", "acm_nitsurat"):
                    raise
                warnings.warn(
                    f"Decorative element {element_id} ({element.src!r}) could not be rendered: {err}",
                    RuntimeWarning,
                    stacklevel=2,
                )
        elif isinstance(element, RoleBadgeEl):
            label, icon = _role_info(role)
            if role not in spec.theme.role_colors:
                warnings.warn(
                    f"Role {role!r} has no configured color; the primary theme color is used.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            fragments.append(
                draw_role_badge(
                    element,
                    spec.theme,
                    role,
                    label,
                    element_id,
                    font_faces,
                    icon=icon,
                )
            )
        elif isinstance(element, QrEl):
            payload = person.get_field(element.field)
            if payload:
                fragments.append(draw_qr(element, payload, spec.theme, role, element_id))
        elif isinstance(element, SvgAssetEl):
            try:
                path = _svg_asset_path(element.src)
                fragments.append(draw_svg_asset(element, file_to_data_uri(path), element_id))
            except (FileNotFoundError, ValueError) as err:
                warnings.warn(
                    f"SVG asset {element_id} ({element.src!r}) could not be rendered: {err}",
                    RuntimeWarning,
                    stacklevel=2,
                )
        else:
            raise TypeError(f"Unsupported layout element model: {type(element).__name__}")


    width = spec.page.canvas_w_mm
    height = spec.page.canvas_h_mm
    trim_x = spec.page.bleed_mm
    trim_y = spec.page.bleed_mm
    trim_width = spec.page.width_mm
    trim_height = spec.page.height_mm
    safe = spec.page.safe_mm
    guides = _debug_guides(
        width, height, trim_x, trim_y, trim_width, trim_height, safe, debug_guides
    )
    svg_body = "\n".join(fragments)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width:g}mm" height="{height:g}mm" viewBox="0 0 {width:g} {height:g}" '
        f'data-trim-box="{trim_x:g} {trim_y:g} {trim_width:g} {trim_height:g}" '
        f'data-safe-box="{trim_x + safe:g} {trim_y + safe:g} '
        f'{trim_width - 2 * safe:g} {trim_height - 2 * safe:g}">\n'
        f'{_font_face_style(font_faces)}\n{svg_body}\n{guides}</svg>'
    )


def _font_face_style(font_faces: dict[tuple[str, str], Path]) -> str:
    rules = []
    for (family, weight), path in sorted(font_faces.items()):
        uri = file_to_data_uri(path)
        css_family = family.replace("\\", "\\\\").replace('"', '\\"').replace("<", "\\3c ")
        rules.append(
            f'@font-face{{font-family:"{css_family}";font-style:normal;font-weight:{weight};'
            f'src:url("{uri}") format("truetype")}}'
        )
    return f"<style>{''.join(rules)}</style>" if rules else ""


def _debug_guides(
    width: float,
    height: float,
    trim_x: float,
    trim_y: float,
    trim_width: float,
    trim_height: float,
    safe: float,
    enabled: bool,
) -> str:
    if not enabled:
        return ""
    return (
        '<g id="debug-guides" fill="none" stroke-dasharray="1 1">'
        f'<rect id="guide-bleed" x="0" y="0" width="{width:g}" height="{height:g}" stroke="#E11D48" stroke-width="0.3"/>'
        f'<rect id="guide-trim" x="{trim_x:g}" y="{trim_y:g}" width="{trim_width:g}" height="{trim_height:g}" stroke="#10B981" stroke-width="0.3"/>'
        f'<rect id="guide-safe" x="{trim_x + safe:g}" y="{trim_y + safe:g}" '
        f'width="{trim_width - 2 * safe:g}" height="{trim_height - 2 * safe:g}" stroke="#3B82F6" stroke-width="0.3"/>'
        '</g>'
    )


def _logo_path(spec: DesignSpec, element: LogoEl) -> Path:
    relative_path = spec.brand.logos.get(element.src) if spec.brand and spec.brand.logos else None
    if relative_path is None and spec.brand and spec.brand.logos:
        alias = {
            "acm": "acm_nitsurat",
            "acm_nitsurat": "acm",
            "logo_acm": "acm_nitsurat",
            "logo_svnit": "svnit",
            "bg_tech_grid": "bg_image",
            "bg_image": "bg_tech_grid",
            "bg_custom": "bg_image",
        }.get(element.src)
        if alias:
            relative_path = spec.brand.logos.get(alias)
    if relative_path is None:
        if element.src in ("acm", "acm_nitsurat", "logo_acm"):
            relative_path = "assets/logos/acm_nitsurat.svg"
        elif element.src in ("svnit", "logo_svnit"):
            relative_path = "assets/logos/svnit.svg"
        elif element.src in ("bg_image", "bg_tech_grid"):
            relative_path = "assets/art/bg_tech_grid.svg"
        elif element.src in ("bg_circuit_lines", "circuit_lines"):
            relative_path = "assets/art/bg_circuit_lines.svg"
        elif element.src in ("bg_geometric_mesh", "geometric_mesh"):
            relative_path = "assets/art/bg_geometric_mesh.svg"
        elif element.src in ("bg_svnit_watermark", "svnit_watermark"):
            relative_path = "assets/art/bg_svnit_watermark.svg"
    if relative_path is None:
        raise ValueError(f"Logo {element.src!r} is not configured in the brand kit")

    clean_p = relative_path.lstrip("/")
    for prefix in ("frontend/public/art/", "frontend/public/logos/", "frontend/public/", "art/", "logos/"):
        if clean_p.startswith(prefix):
            clean_p = ("assets/art/" if "art" in prefix else "assets/logos/" if "logos" in prefix else "assets/") + clean_p[len(prefix):]
            break

    path = asset_path(clean_p)
    if not path.is_file():
        from app.config import ROOT
        cand = ROOT / clean_p
        if cand.is_file():
            return cand
        raise FileNotFoundError(f"Configured logo file does not exist: {relative_path}")
    return path


def _svg_asset_path(source: str) -> Path:
    relative_path = source if source.startswith("assets/") else f"assets/art/{source}"
    path = asset_path(relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"SVG asset file does not exist: {relative_path}")
    return path


def _asset_aspect_ratio(path: Path) -> float:
    if path.suffix.lower() == ".svg":
        root = ElementTree.parse(path).getroot()
        view_box = root.get("viewBox") or root.get("viewbox")
        if view_box:
            values = [float(value) for value in view_box.replace(",", " ").split()]
            if len(values) == 4 and values[2] > 0 and values[3] > 0:
                return values[2] / values[3]
        width, height = root.get("width"), root.get("height")
        if width and height:
            return _svg_length(width) / _svg_length(height)
        raise ValueError(f"Logo SVG has no usable viewBox or dimensions: {path}")

    from PIL import Image

    with Image.open(path) as image:
        width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError(f"Logo image dimensions must be positive: {path}")
    return width / height


def _svg_length(value: str) -> float:
    number = "".join(character for character in value if character.isdigit() or character in ".-")
    parsed = float(number)
    if parsed <= 0:
        raise ValueError(f"SVG dimension must be positive: {value!r}")
    return parsed


def _photo_data_uri(person: Person, element: PhotoEl) -> str | None:
    if not person.photo:
        return None
    photo_name = person.photo.replace("\\", "/")
    for prefix in ("sample_data/photos/", "photos/"):
        if photo_name.startswith(prefix):
            photo_name = photo_name[len(prefix):]
            break
    if not photo_name or Path(photo_name).name != photo_name:
        raise ValueError(f"Photo must be a file name under sample_data/photos/: {person.photo!r}")
    path = (SAMPLE_DATA / "photos" / photo_name).resolve()
    photo_root = (SAMPLE_DATA / "photos").resolve()
    if photo_root not in path.parents:
        raise ValueError(f"Photo path must remain under {photo_root}: {person.photo!r}")
    if not path.is_file():
        warnings.warn(
            f"Photo file was not found: {path}; showing initials instead.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None

    from PIL import Image, ImageOps
    from io import BytesIO

    pixel_size = (
        max(1, round(element.w * 300 / 25.4)),
        max(1, round(element.h * 300 / 25.4)),
    )
    with Image.open(path) as source:
        photo = ImageOps.fit(
            source.convert("RGB"),
            pixel_size,
            method=Image.Resampling.LANCZOS,
        )
    output = BytesIO()
    photo.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@lru_cache(maxsize=1)
def _roles_config() -> dict[str, dict[str, str]]:
    path = TEMPLATES / "roles.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Role configuration must be an array: {path}")
    result = {}
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError(f"Invalid role entry in {path}")
        label = item.get("badge_text")
        if not isinstance(label, str) or not label:
            raise ValueError(f"Role {item['id']!r} has no badge_text in {path}")
        result[item["id"]] = {
            "label": label,
            "icon": item.get("icon") or "circle",
        }
    return result


def _role_info(role: str) -> tuple[str, str]:
    config = _roles_config()
    if role not in config:
        warnings.warn(
            f"Role {role!r} is not configured in roles.json; displaying its supplied value.",
            RuntimeWarning,
            stacklevel=2,
        )
        return role.upper(), "circle"
    return config[role]["label"], config[role].get("icon", "circle")


def _role_label(role: str) -> str:
    label, _ = _role_info(role)
    return label


def _initials(name: str) -> str:
    parts = name.split()
    return "".join(part[0] for part in (parts if len(parts) == 1 else (parts[0], parts[-1]))).upper()
