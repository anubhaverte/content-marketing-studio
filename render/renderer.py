"""Build a data-driven SVG card from a normalized spec, layout, and theme."""

from __future__ import annotations

import base64
import re
import warnings
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from render import spec_adapter
from render.loaders import LAYOUTS_DIR, THEMES_DIR, load_layout, load_theme
from render.photo import best_contrast_text_color, initials, initials_markup, photo_markup
from render.qr import qr_markup
from render.text_fit import find_font_file, fit_text, measure_text_vertical_bounds


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ALLOWED_LAYOUT_COLORS = frozenset(
    {"primary", "secondary", "background", "text", "text_on_primary", "accent"}
)
ROLE_LABELS = {
    "participant": "PARTICIPANT",
    "organizer": "ORGANIZER",
    "mentor": "MENTOR",
    "volunteer": "VOLUNTEER",
}
ROLE_CUES = {
    "participant": "circle",
    "organizer": "square",
    "mentor": "triangle",
    "volunteer": "diamond",
}
def render_card(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    *,
    layouts_dir: Path = LAYOUTS_DIR,
    themes_dir: Path = THEMES_DIR,
) -> str:
    """Return one complete SVG card for a person."""
    layout = load_layout(spec_adapter.spec_layout(spec), layouts_dir)
    theme = load_theme(spec_adapter.spec_theme(spec), themes_dir)
    return _render(spec, person, layout, theme)


def render_preview(spec: spec_adapter.DesignSpec, role: str) -> str:
    """Render a preview using the first bundled sample person for a role."""
    people = spec_adapter.load_people()
    person = spec_adapter.sample_person_for_role(role, people)
    return render_card(spec, person)


def _render(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    layout: dict[str, Any],
    theme: dict[str, Any],
) -> str:
    """Build SVG markup using only normalized Design Spec accessors."""
    layout_file = str(layout.get("_source_file", "layout file"))
    theme_file = str(theme.get("_source_file", "theme file"))
    role = spec_adapter.person_role(person)
    colors = theme.get("colors")
    role_colors = theme.get("role_colors")
    fonts = theme.get("fonts")
    if not isinstance(colors, dict):
        raise ValueError(f"Theme colors must be an object in {theme_file}")
    if not isinstance(role_colors, dict):
        raise ValueError(f"Theme role_colors must be an object in {theme_file}")
    if role not in role_colors:
        raise ValueError(f"Theme {theme_file} has no color for role {role!r}")
    role_values = [role_colors.get(known_role) for known_role in spec_adapter.ROLES]
    if any(
        not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value)
        for value in role_values
    ):
        raise ValueError(f"Theme {theme_file} must define a valid hex color for every role")
    if len(set(role_values)) != len(spec_adapter.ROLES):
        raise ValueError(f"Theme {theme_file} must give roles clearly different colors")
    if not isinstance(fonts, dict):
        raise ValueError(f"Theme fonts must be an object in {theme_file}")
    font_families = _font_families(fonts, theme_file)
    selected_family, font_path = find_font_file(font_families)
    width, height, trim_x, trim_y, trim_width, trim_height = spec_adapter.canvas_geometry(spec)
    safe = spec_adapter.safe_inset(spec)
    elements = layout.get("elements")
    if not isinstance(elements, list):
        raise ValueError(f"Layout elements must be an array in {layout_file}")
    role_area = layout.get("role_area")
    requested_logos = set(spec_adapter.spec_logos(spec))
    context = {
        "spec": spec,
        "person": person,
        "role": role,
        "layout": layout,
        "theme": theme,
        "colors": colors,
        "role_color": role_colors[role],
        "family": f'"{selected_family}"',
        "font_families": font_families,
        "font_path": font_path,
        "font_faces": {},
        "requested_logos": requested_logos,
        "layout_file": layout_file,
        "theme_file": theme_file,
    }
    body = [
        f'<rect x="0" y="0" width="{_num(width)}" height="{_num(height)}" '
        f'fill="{_attr(_theme_color(colors, "secondary", theme_file))}"/>',
        f'<rect x="{_num(trim_x)}" y="{_num(trim_y)}" width="{_num(trim_width)}" '
        f'height="{_num(trim_height)}" fill="{_attr(_theme_color(colors, "background", theme_file))}"/>',
    ]
    for element in elements:
        if not isinstance(element, dict):
            raise ValueError(f"Each layout element must be an object in {layout_file}")
        _element_color(element, context)
        element_type = element.get("type")
        renderer = {
            "rect": _render_rect,
            "text": _render_text,
            "logo": _render_logo,
            "photo": _render_photo,
            "image": _render_image,
            "qr": _render_qr,
        }.get(element_type)
        if renderer is None:
            raise ValueError(f"Unknown layout element type {element_type!r} in {layout_file}")
        body.append(renderer(element, context))
        if element.get("role_area") is True:
            if not isinstance(role_area, dict):
                raise ValueError(f"Role-area element has no role_area settings in {layout_file}")
            body.append(_render_role_details(role_area, context))

    root_attributes = (
        f'width="{_num(width)}mm" height="{_num(height)}mm" '
        f'viewBox="0 0 {_num(width)} {_num(height)}" '
        f'data-trim-box="{_num(trim_x)} {_num(trim_y)} {_num(trim_width)} {_num(trim_height)}" '
        f'data-safe-box="{_num(trim_x + safe)} {_num(trim_y + safe)} '
        f'{_num(trim_width - 2 * safe)} {_num(trim_height - 2 * safe)}"'
    )
    logo_statuses = []
    for logo in sorted(requested_logos):
        status = "embedded" if _find_asset(logo) is not None else "placeholder"
        logo_statuses.append(f'data-logo-{_attr(logo)}="{status}"')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'{root_attributes} {" ".join(logo_statuses)}>\n'
        + _font_face_style(context["font_faces"])
        + "\n".join(body)
        + "\n</svg>"
    )


def _render_rect(element: dict[str, Any], context: dict[str, Any]) -> str:
    """Render a named-color rectangle."""
    x, y, width, height = _geometry(element, context["layout_file"])
    color = context["role_color"] if element.get("role_area") is True else _element_color(element, context)
    radius = element.get("radius", 0)
    return (
        f'<rect id="{_attr(element.get("id", "rect"))}" x="{_num(x)}" y="{_num(y)}" '
        f'width="{_num(width)}" height="{_num(height)}" rx="{_num(radius)}" '
        f'fill="{_attr(color)}"/>'
    )


def _render_text(element: dict[str, Any], context: dict[str, Any]) -> str:
    """Render escaped text from a normalized event or person value."""
    x, y, width, height = _geometry(element, context["layout_file"])
    field = element.get("data")
    value = _data_value(str(field), context)
    if value is None or not value.strip():
        if field == "event.name":
            value = "EVENT NAME"
            warnings.warn("event.name is null or empty; drew the visible EVENT NAME placeholder")
        elif field == "person.name":
            value = "NAME NOT PROVIDED"
            warnings.warn("Person name is missing; drew the visible NAME NOT PROVIDED fallback")
        else:
            value = f"{str(field).rsplit('.', 1)[-1].replace('_', ' ').upper()} NOT PROVIDED"
            warnings.warn(f"Data for {field!r} is missing; drew a visible fallback")
    font_size = _positive_layout_number(element, "font_size", context["layout_file"])
    weight = element.get("weight", "400")
    alignment = element.get("alignment", "start")
    if alignment not in {"start", "middle", "end"}:
        raise ValueError(f"Unknown text alignment {alignment!r} in {context['layout_file']}")
    min_font_size = _positive_layout_number(element, "min_font_size", context["layout_file"])
    max_width = min(width, _positive_layout_number(element, "max_width", context["layout_file"]))
    max_lines = _positive_layout_integer(element, "max_lines", context["layout_file"])
    font_family, font_path = find_font_file(context["font_families"], str(weight))
    context["font_faces"][(font_family, str(weight))] = font_path
    line_capacity = max(1, int(height / (min_font_size * 1.2)))
    result = fit_text(
        value,
        font_path=font_path,
        font_size=font_size,
        min_font_size=min_font_size,
        max_width=max_width,
        max_lines=min(max_lines, line_capacity),
    )
    color = _element_color(element, context)
    left = x - max_width / 2 if alignment == "middle" else (x - max_width if alignment == "end" else x)
    clip_id = f"{element.get('id', 'text')}-clip"
    line_height = result.font_size * 1.2
    line_bounds = [
        measure_text_vertical_bounds(line, font_path, result.font_size)
        for line in result.lines
    ]
    top = min(index * line_height - ascent for index, (ascent, _) in enumerate(line_bounds))
    bottom = max(index * line_height + descent for index, (_, descent) in enumerate(line_bounds))
    first_baseline = y - (top + bottom) / 2
    tspans = "".join(
        f'<tspan x="{_num(x)}" y="{_num(first_baseline + index * line_height)}">{_text(line)}</tspan>'
        for index, line in enumerate(result.lines)
    )
    return (
        f'<defs><clipPath id="{_attr(clip_id)}"><rect x="{_num(left)}" '
        f'y="{_num(y - height / 2)}" width="{_num(max_width)}" height="{_num(height)}"/></clipPath></defs>'
        f'<text id="{_attr(element.get("id", "text"))}" data-shortened="{str(result.shortened).lower()}" '
        f'x="{_num(x)}" y="{_num(first_baseline)}" text-anchor="{alignment}" '
        f'font-family="{_attr(font_family)}" font-size="{_num(result.font_size)}" '
        f'font-weight="{_attr(weight)}" fill="{_attr(color)}" clip-path="url(#{_attr(clip_id)})">'
        f'{tspans}</text>'
    )


def _render_logo(element: dict[str, Any], context: dict[str, Any]) -> str:
    """Embed a Phase 1-style logo at a fixed height without stretching it."""
    logo_name = element.get("data")
    if not isinstance(logo_name, str) or not logo_name:
        raise ValueError(f"Logo element needs a data logo name in {context['layout_file']}")
    if logo_name not in context["requested_logos"]:
        return ""
    x, y, slot_width, slot_height = _geometry(element, context["layout_file"])
    path = _find_asset(logo_name)
    element_id = f"logo-{logo_name}"
    if path is None:
        warnings.warn(f"Missing logo: assets/{logo_name}.svg or assets/{logo_name}.png")
        background_color = _theme_color(context["colors"], "accent", context["theme_file"])
        text_color_name, text_color = best_contrast_text_color(
            background_color, context["colors"]
        )
        placeholder = _missing_asset_markup(
            element_id,
            f"LOGO MISSING: {logo_name}",
            x,
            y,
            slot_width,
            slot_height,
            background_color=background_color,
            background_color_name="accent",
            text_color_name=text_color_name,
            text_color=text_color,
        )
        return placeholder.replace(
            'data-asset-status="placeholder"',
            'data-asset-status="placeholder" data-logo-status="placeholder"',
            1,
        )
    ratio = _asset_ratio(path)
    logo_height = min(8.0, slot_height)
    logo_width = min(slot_width, ratio * logo_height)
    logo_x = x + (slot_width - logo_width) / 2
    logo_y = y + (slot_height - logo_height) / 2
    media_type = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f'<image id="{_attr(element_id)}" data-logo-status="embedded" x="{_num(logo_x)}" '
        f'y="{_num(logo_y)}" width="{_num(logo_width)}" height="{_num(logo_height)}" '
        f'preserveAspectRatio="xMidYMid meet" href="data:{media_type};base64,{encoded}"/>'
    )


def _render_photo(element: dict[str, Any], context: dict[str, Any]) -> str:
    """Embed a centered, clipped photo or show initials for unavailable data."""
    x, y, width, height = _geometry(element, context["layout_file"])
    photo_path = spec_adapter.person_photo_path(context["person"])
    shape = element.get("shape", "circle")
    if shape not in {"circle", "rounded_rect"}:
        raise ValueError(f"Unknown photo shape {shape!r} in {context['layout_file']}")
    radius = float(element.get("radius", min(width, height) * 0.12))
    if photo_path is not None:
        try:
            if photo_path.is_file():
                markup, _ = photo_markup(
                    photo_path, element_id="person-photo", x=x, y=y, width=width, height=height,
                    shape=shape, radius=radius,
                )
                return markup
            warnings.warn(f"Person photo was not found: {photo_path}")
        except (OSError, ValueError) as error:
            warnings.warn(f"Person photo cannot be read ({photo_path}): {error}")
    else:
        warnings.warn("Person photo is missing; drew an initials fallback")
    name = spec_adapter.person_value(context["person"], "name")
    background_color = _element_color(element, context)
    text_color_name, text_color = best_contrast_text_color(background_color, context["colors"])
    return initials_markup(
        element_id="person-photo", label=initials(name), x=x, y=y, width=width,
        height=height, shape=shape, radius=radius,
        color=background_color, text_color=text_color, text_color_name=text_color_name,
    )


def _render_qr(element: dict[str, Any], context: dict[str, Any]) -> str:
    """Render an attendance QR only when its real URL prefix and person ID exist."""
    base_url = spec_adapter.attendance_url_base(context["spec"])
    if base_url is None:
        warnings.warn("attendance_url_base is null; skipped QR code")
        return ""
    person_id = spec_adapter.person_id(context["person"])
    if not person_id:
        warnings.warn("Person ID is missing; skipped attendance QR code")
        return ""
    x, y, width, height = _geometry(element, context["layout_file"])
    size = _positive_layout_number(element, "qr_size_mm", context["layout_file"])
    if size < 12 or size > width or size > height:
        raise ValueError(f"QR size must be at least 12 mm and fit its layout box in {context['layout_file']}")
    color = _element_color(element, context)
    background = _theme_color(context["colors"], "background", context["theme_file"])
    return qr_markup(
        base_url + person_id, element_id=_attr(element.get("id", "qr")), x=x, y=y,
        size=size, color=color, background=background,
    )


def _render_image(element: dict[str, Any], context: dict[str, Any]) -> str:
    """Embed a local image proportionally, or display a visible placeholder."""
    x, y, width, height = _geometry(element, context["layout_file"])
    source = element.get("data")
    if isinstance(source, str):
        path = (ASSETS_DIR / source).resolve()
        if path.is_file() and path.parent == ASSETS_DIR.resolve():
            return _image_markup(path, str(element.get("id", "image")), x, y, width, height)
    warnings.warn(f"Image asset {source!r} is missing under assets/")
    background_color = _theme_color(context["colors"], "accent", context["theme_file"])
    text_color_name, text_color = best_contrast_text_color(
        background_color, context["colors"]
    )
    return _missing_asset_markup(
        str(element.get("id", "image")),
        f"IMAGE MISSING: {source or 'not specified'}",
        x,
        y,
        width,
        height,
        background_color=background_color,
        background_color_name="accent",
        text_color_name=text_color_name,
        text_color=text_color,
    )


def _render_role_details(role_area: dict[str, Any], context: dict[str, Any]) -> str:
    """Draw distinct role labels and shape cues in the role-color area."""
    label = role_area.get("label")
    cue = role_area.get("cue")
    if not isinstance(label, dict) or not isinstance(cue, dict):
        raise ValueError(f"Role area needs label and cue settings in {context['layout_file']}")
    label_text = ROLE_LABELS[context["role"]]
    label_position = label.get("position")
    if not isinstance(label_position, dict):
        raise ValueError(f"Role-area label needs a position object in {context['layout_file']}")
    label_x, label_y = _point(label_position, context["layout_file"])
    cue_x, cue_y, cue_width, cue_height = _geometry(cue, context["layout_file"])
    label_color_name, label_color = best_contrast_text_color(
        context["role_color"], context["colors"]
    )
    label_size = _positive_layout_number(label, "font_size", context["layout_file"])
    label_family, label_font_path = find_font_file(context["font_families"], "700")
    context["font_faces"][(label_family, "700")] = label_font_path
    label_markup = (
        f'<text id="role-label" x="{_num(label_x)}" y="{_num(label_y)}" '
        f'data-theme-color="{_attr(label_color_name)}" '
        f'text-anchor="{_attr(label.get("alignment", "middle"))}" '
        f'font-family="{_attr(label_family)}" font-size="{_num(label_size)}" '
        f'font-weight="700" fill="{_attr(label_color)}">{_text(label_text)}</text>'
    )
    shape = ROLE_CUES[context["role"]]
    cue_markup = _cue_markup(shape, cue_x, cue_y, cue_width, cue_height, label_color)
    return f'<g id="role-details">{label_markup}<g id="role-cue" data-cue="{shape}">{cue_markup}</g></g>'


def _cue_markup(shape: str, x: float, y: float, width: float, height: float, color: str) -> str:
    """Render one of the four high-contrast role shape cues."""
    cx, cy = x + width / 2, y + height / 2
    if shape == "circle":
        return f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(min(width, height) / 2)}" fill="{_attr(color)}"/>'
    if shape == "square":
        return f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(width)}" height="{_num(height)}" fill="{_attr(color)}"/>'
    if shape == "triangle":
        points = f"{_num(cx)},{_num(y)} {_num(x + width)},{_num(y + height)} {_num(x)},{_num(y + height)}"
    else:
        points = f"{_num(cx)},{_num(y)} {_num(x + width)},{_num(cy)} {_num(cx)},{_num(y + height)} {_num(x)},{_num(cy)}"
    return f'<polygon points="{points}" fill="{_attr(color)}"/>'


def _data_value(field: str, context: dict[str, Any]) -> str | None:
    """Resolve the small temporary data-field vocabulary."""
    if field.startswith("person."):
        return spec_adapter.person_value(context["person"], field.removeprefix("person."))
    if field.startswith("event."):
        return spec_adapter.event_value(context["spec"], field.removeprefix("event."))
    raise ValueError(f"Unknown text data field {field!r} in {context['layout_file']}")


def _element_color(element: dict[str, Any], context: dict[str, Any]) -> str:
    """Resolve a layout color name from the selected theme."""
    name = element.get("color")
    if name not in ALLOWED_LAYOUT_COLORS:
        raise ValueError(f"Unknown layout color {name!r} in {context['layout_file']}")
    return _theme_color(context["colors"], name, context["theme_file"])


def _theme_color(colors: dict[str, Any], name: str, theme_file: str) -> str:
    """Return and validate one named color from a theme file."""
    value = colors.get(name)
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise ValueError(f"Unknown or invalid color name {name!r} in {theme_file}")
    return value


def _font_families(fonts: dict[str, Any], theme_file: str) -> list[str]:
    """Return configured heading and body font families in fallback order."""
    heading = fonts.get("heading")
    if not isinstance(heading, list) or not heading or not all(isinstance(item, str) for item in heading):
        raise ValueError(f"Theme heading fonts must be a non-empty string array in {theme_file}")
    body = fonts.get("body", [])
    if not isinstance(body, list) or not all(isinstance(item, str) for item in body):
        raise ValueError(f"Theme body fonts must be a string array in {theme_file}")
    return heading + body


def _geometry(element: dict[str, Any], layout_file: str) -> tuple[float, float, float, float]:
    """Read validated x/y/width/height values from layout JSON."""
    position = element.get("position")
    size = element.get("size")
    if not isinstance(position, dict) or not isinstance(size, dict):
        raise ValueError(f"Layout element needs position and size objects in {layout_file}")
    x, y = _point(position, layout_file)
    width = _positive_layout_number(size, "width", layout_file)
    height = _positive_layout_number(size, "height", layout_file)
    return x, y, width, height


def _point(point: dict[str, Any], layout_file: str) -> tuple[float, float]:
    """Read validated x/y coordinates from layout JSON."""
    return _layout_number(point, "x", layout_file), _layout_number(point, "y", layout_file)


def _positive_layout_number(data: dict[str, Any], field: str, layout_file: str) -> float:
    """Read a positive numeric layout value."""
    value = _layout_number(data, field, layout_file)
    if value <= 0:
        raise ValueError(f"Layout value {field!r} must be greater than zero in {layout_file}")
    return value


def _positive_layout_integer(data: dict[str, Any], field: str, layout_file: str) -> int:
    """Read a positive integer layout value."""
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Layout value {field!r} must be a positive integer in {layout_file}")
    return value


def _layout_number(data: dict[str, Any], field: str, layout_file: str) -> float:
    """Read a numeric layout value."""
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Layout value {field!r} must be numeric in {layout_file}")
    return float(value)


def _find_asset(name: str) -> Path | None:
    """Find a logo in the shared assets directory without flattening its path."""
    asset_name = {"acm": "acm_nitsurat"}.get(name, name)
    for directory in (ASSETS_DIR / "logos", ASSETS_DIR):
        for suffix in (".svg", ".png"):
            path = directory / f"{asset_name}{suffix}"
            if path.is_file():
                return path
    return None


def _font_face_style(font_faces: dict[tuple[str, str], Path]) -> str:
    """Embed the exact font files used for measuring text in the SVG."""
    rules = []
    for (family, weight), path in sorted(font_faces.items()):
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            f'@font-face{{font-family:"{_attr(family)}";font-style:normal;'
            f'font-weight:{_attr(weight)};src:url("data:font/ttf;base64,{encoded}") '
            'format("truetype")}}'
        )
    return f"<style>{''.join(rules)}</style>\n" if rules else ""


def _asset_ratio(path: Path) -> float:
    """Read a PNG dimension ratio or an SVG viewBox ratio."""
    if path.suffix.lower() == ".png":
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
    elif path.suffix.lower() == ".svg":
        import xml.etree.ElementTree as element_tree

        root = element_tree.parse(path).getroot()
        view_box = root.get("viewBox") or root.get("viewbox")
        if not view_box:
            raise ValueError(f"SVG logo must have a viewBox: {path}")
        values = [float(value) for value in view_box.replace(",", " ").split()]
        if len(values) != 4:
            raise ValueError(f"SVG viewBox must contain four numbers: {path}")
        width, height = values[2], values[3]
    else:
        raise ValueError(f"Logo must be SVG or PNG: {path}")
    if width <= 0 or height <= 0:
        raise ValueError(f"Logo dimensions must be positive: {path}")
    return width / height


def _image_markup(path: Path, element_id: str, x: float, y: float, width: float, height: float) -> str:
    """Embed a local SVG or PNG image proportionally in its layout box."""
    ratio = _asset_ratio(path)
    image_width = min(width, height * ratio)
    image_height = min(height, width / ratio)
    image_x = x + (width - image_width) / 2
    image_y = y + (height - image_height) / 2
    media_type = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f'<image id="{_attr(element_id)}" x="{_num(image_x)}" y="{_num(image_y)}" '
        f'width="{_num(image_width)}" height="{_num(image_height)}" '
        f'preserveAspectRatio="xMidYMid meet" href="data:{media_type};base64,{encoded}"/>'
    )


def _missing_asset_markup(
    element_id: str,
    label: str,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    background_color: str,
    background_color_name: str,
    text_color: str,
    text_color_name: str,
) -> str:
    """Draw an accessible, visibly labelled missing-image placeholder."""
    return (
        f'<g id="{_attr(element_id)}" data-asset-status="placeholder">'
        f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(width)}" height="{_num(height)}" '
        f'rx="0.6" fill="{_attr(background_color)}" data-theme-color="{_attr(background_color_name)}" '
        f'stroke="{_attr(text_color)}" stroke-dasharray="0.8 0.5"/>'
        f'<text id="{_attr(element_id)}-label" data-theme-color="{_attr(text_color_name)}" '
        f'x="{_num(x + width / 2)}" y="{_num(y + height / 2)}" text-anchor="middle" '
        f'font-size="1.5" fill="{_attr(text_color)}">{_text(label)}</text></g>'
    )


def _num(value: float) -> str:
    """Format a numeric SVG value without needless trailing zeroes."""
    return f"{value:g}"


def _text(value: str) -> str:
    """Escape text nodes, including quotes, before writing SVG markup."""
    return escape(value, {'"': "&quot;", "'": "&apos;"})


def _attr(value: Any) -> str:
    """Escape an arbitrary value for safe use in an XML attribute."""
    return _text(str(value))
