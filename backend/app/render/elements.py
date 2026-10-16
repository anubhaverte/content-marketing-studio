"""Draw each supported layout element as editable SVG markup."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from app.spec.schema import GradientFill
from app.render.qr import qr_svg_path
from app.render.text_fit import fit_text, measure_text_vertical_bounds, resolve_font


def draw_rect(el: Any, theme: Any, role: str, element_id: str) -> str:
    fill, defs = _paint(el.fill, theme, role, f"{element_id}-fill")
    stroke = _color(el.stroke, theme, role)
    dash = _dash(el.dash)
    return (
        f'{defs}<rect id="{_attr(element_id)}" x="{el.x:g}" y="{el.y:g}" '
        f'width="{el.w:g}" height="{el.h:g}" rx="{el.radius:g}" '
        f'fill="{_attr(fill)}" stroke="{_attr(stroke)}" '
        f'stroke-width="{el.stroke_width:g}" opacity="{el.opacity:g}"{dash}/>'
    )


def draw_line(el: Any, theme: Any, role: str, element_id: str) -> str:
    dash = _dash(el.dash)
    return (
        f'<line id="{_attr(element_id)}" x1="{el.x1:g}" y1="{el.y1:g}" '
        f'x2="{el.x2:g}" y2="{el.y2:g}" stroke="{_attr(_color(el.stroke, theme, role))}" '
        f'stroke-width="{el.stroke_width:g}" opacity="{el.opacity:g}"{dash}/>'
    )


def draw_circle(el: Any, theme: Any, role: str, element_id: str) -> str:
    fill, defs = _paint(el.fill, theme, role, f"{element_id}-fill")
    return (
        f'{defs}<circle id="{_attr(element_id)}" cx="{el.cx:g}" cy="{el.cy:g}" '
        f'r="{el.r:g}" fill="{_attr(fill)}" '
        f'stroke="{_attr(_color(el.stroke, theme, role))}" '
        f'stroke-width="{el.stroke_width:g}" opacity="{el.opacity:g}"/>'
    )


def draw_text(
    el: Any,
    theme: Any,
    text: str,
    role: str,
    element_id: str,
    fonts_used: dict[tuple[str, str], Path],
) -> str:
    """Fit and emit text without changing its source data."""
    if el.uppercase:
        text = text.upper()
    family = theme.fonts.heading if el.font == "heading" else theme.fonts.body
    weight = "700" if el.bold else "400"
    resolved_family, font_path = resolve_font(family, el.bold)
    fonts_used[(resolved_family, weight)] = font_path
    result = fit_text(text, font_path, el.w, el.max_font, el.min_font, el.max_lines)
    font_size = result["font_size"]
    lines = result["lines"]
    anchor = {"left": "start", "center": "middle", "right": "end"}[el.align]
    x = el.x if el.align == "left" else el.x + el.w / 2 if el.align == "center" else el.x + el.w
    first_ascent, _ = measure_text_vertical_bounds(lines[0], font_path, font_size)
    line_height = font_size * 1.2
    tspans = "".join(
        f'<tspan x="{x:g}" y="{el.y + first_ascent + index * line_height:g}">{_text(line)}</tspan>'
        for index, line in enumerate(lines)
    )
    return (
        f'<text id="{_attr(element_id)}" data-field="{_attr(el.field or "value")}" '
        f'data-shortened="{str(result["shortened"]).lower()}" x="{x:g}" '
        f'y="{el.y + first_ascent:g}" '
        f'text-anchor="{anchor}" font-family="{_attr(resolved_family)}" '
        f'font-size="{font_size:g}" font-weight="{weight}" '
        f'fill="{_attr(_color(el.color, theme, role))}">{tspans}</text>'
    )


def draw_photo(
    el: Any,
    photo_uri: str | None,
    initials: str,
    theme: Any,
    element_id: str,
    fonts_used: dict[tuple[str, str], Path],
) -> str:
    shape = _clip_shape(el.shape, el.x, el.y, el.w, el.h, el.radius)
    clip_id = f"{element_id}-clip"
    clip = f'<defs><clipPath id="{_attr(clip_id)}">{shape}</clipPath></defs>'
    if photo_uri:
        return (
            f'{clip}<image id="{_attr(element_id)}" data-photo-status="embedded" '
            f'x="{el.x:g}" y="{el.y:g}" width="{el.w:g}" height="{el.h:g}" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{_attr(clip_id)})" '
            f'href="{_attr(photo_uri)}"/>'
        )

    family, font_path = resolve_font(theme.fonts.body, True)
    fonts_used[(family, "700")] = font_path
    background = _color("secondary", theme, "")
    foreground = _contrast_text(background, theme.colors.text)
    size = min(el.w, el.h) * 0.3
    return (
        f'{clip}<g id="{_attr(element_id)}" data-photo-status="fallback">'
        f'<rect x="{el.x:g}" y="{el.y:g}" width="{el.w:g}" height="{el.h:g}" '
        f'fill="{_attr(background)}" clip-path="url(#{_attr(clip_id)})"/>'
        f'<text x="{el.x + el.w / 2:g}" y="{el.y + el.h / 2:g}" '
        f'dominant-baseline="middle" text-anchor="middle" '
        f'font-family="{_attr(family)}" font-size="{size:g}" font-weight="700" '
        f'fill="{_attr(foreground)}">{_text(initials)}</text></g>'
    )


def draw_logo(
    el: Any,
    logo_uri: str,
    aspect_ratio: float,
    element_id: str,
    logo_name: str,
) -> str:
    height = el.h if el.h is not None else el.w / aspect_ratio
    return (
        f'<image id="{_attr(element_id)}" data-logo-name="{_attr(logo_name)}" '
        f'data-logo-status="embedded" data-logo-fit="contain" '
        f'x="{el.x:g}" y="{el.y:g}" '
        f'width="{el.w:g}" height="{height:g}" preserveAspectRatio="xMidYMid meet" '
        f'href="{_attr(logo_uri)}"/>'
    )


def draw_role_badge(
    el: Any,
    theme: Any,
    role: str,
    label: str,
    element_id: str,
    fonts_used: dict[tuple[str, str], Path],
) -> str:
    family, font_path = resolve_font(theme.fonts.body, True)
    fonts_used[(family, "700")] = font_path
    background = theme.role_colors.get(role, theme.colors.primary)
    foreground = _color(el.text_color, theme, role)
    size = min(8.0 * 0.352778, el.h * 0.5)
    baseline = el.y + (el.h + size * 0.7) / 2
    return (
        f'<g id="{_attr(element_id)}" data-role="{_attr(role)}">'
        f'<rect x="{el.x:g}" y="{el.y:g}" width="{el.w:g}" height="{el.h:g}" '
        f'rx="{el.h / 2:g}" fill="{_attr(background)}" stroke="{_attr(foreground)}" '
        f'stroke-width="0.25"/>'
        f'<text data-field="role" x="{el.x + el.w / 2:g}" y="{baseline:g}" text-anchor="middle" '
        f'font-family="{_attr(family)}" font-size="{size:g}" font-weight="700" '
        f'fill="{_attr(foreground)}">{_text(label)}</text></g>'
    )


def draw_qr(el: Any, url: str, theme: Any, role: str, element_id: str) -> str:
    size = min(el.w, el.h)
    if size < 12:
        raise ValueError(f"QR element {element_id!r} must be at least 12 mm")
    return qr_svg_path(
        url,
        size,
        x=el.x,
        y=el.y,
        color=_color(el.fg, theme, role),
        background=_color(el.bg, theme, role),
        element_id=element_id,
    )


def draw_svg_asset(el: Any, asset_uri: str, element_id: str) -> str:
    return (
        f'<image id="{_attr(element_id)}" x="{el.x:g}" y="{el.y:g}" '
        f'width="{el.w:g}" height="{el.h:g}" preserveAspectRatio="xMidYMid meet" '
        f'href="{_attr(asset_uri)}"/>'
    )


def _paint(value: Any, theme: Any, role: str, gradient_id: str) -> tuple[str, str]:
    if not isinstance(value, GradientFill):
        return _color(value, theme, role), ""
    angle = math.radians(value.angle)
    dx, dy = math.cos(angle) / 2, math.sin(angle) / 2
    stops = "".join(
        f'<stop offset="{offset:g}" stop-color="{_attr(_color(color, theme, role))}"/>'
        for offset, color in value.stops
    )
    definition = (
        f'<defs><linearGradient id="{_attr(gradient_id)}" '
        f'x1="{0.5 - dx:g}" y1="{0.5 - dy:g}" x2="{0.5 + dx:g}" y2="{0.5 + dy:g}">'
        f'{stops}</linearGradient></defs>'
    )
    return f"url(#{gradient_id})", definition


def _color(token: str, theme: Any, role: str) -> str:
    if token == "none":
        return "none"
    if token == "role":
        return theme.role_colors.get(role, theme.colors.primary)
    return getattr(theme.colors, token)


def _dash(values: list[float] | None) -> str:
    if not values:
        return ""
    return f' stroke-dasharray="{_attr(" ".join(f"{value:g}" for value in values))}"'


def _clip_shape(shape: str, x: float, y: float, width: float, height: float, radius: float) -> str:
    if shape == "circle":
        return f'<circle cx="{x + width / 2:g}" cy="{y + height / 2:g}" r="{min(width, height) / 2:g}"/>'
    corner = radius if shape == "rounded" else 0
    return f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{corner:g}"/>'


def _contrast_text(background: str, preferred: str) -> str:
    return preferred if _contrast_ratio(background, preferred) >= 4.5 else (
        "#000000" if _contrast_ratio(background, "#000000") >= _contrast_ratio(background, "#FFFFFF")
        else "#FFFFFF"
    )


def _contrast_ratio(first: str, second: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _text(value: str) -> str:
    return escape(value, {'"': "&quot;", "'": "&apos;"})


def _attr(value: str) -> str:
    return _text(str(value))
