"""Temporary stand-in renderer for the layout and theme JSON specifications."""

import base64
import csv
import html
import io
import json
import sys
import warnings
from pathlib import Path
from typing import Any, Callable

import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps
from qrcode.constants import ERROR_CORRECT_M

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import (
    CANVAS_HEIGHT_MM,
    CANVAS_WIDTH_MM,
    MIN_CONTRAST_RATIO,
    SAMPLE_DATA_DIR,
    contrast_ratio,
)
from studio.design_tools.layout import prepare_layout

LAYOUTS_DIR = _repo_root / "studio" / "backend" / "app" / "templates" / "layouts"
THEMES_DIR = _repo_root / "studio" / "backend" / "app" / "templates" / "themes"
LOGOS_DIR = _repo_root / "studio" / "assets" / "logos"
FONTS_DIR = _repo_root / "studio" / "assets" / "fonts"
SVG_WARNING = "TEMPORARY STAND-IN — replace with renderer teammate implementation"


def load_attendees() -> list[dict[str, str]]:
    """Adapt CSV columns to the field names expected by layout templates."""
    csv_path = SAMPLE_DATA_DIR / "test_people.csv"
    attendees = []
    with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
        for row_number, row in enumerate(csv.DictReader(csv_file), start=1):
            attendee_id = row.get("id", "").strip()
            raw_role = row.get("role", "").strip()
            role = raw_role.lower() if raw_role.lower() in {
                "participant",
                "organizer",
                "mentor",
            } else raw_role
            attendees.append(
                {
                    "full_name": row.get("name", ""),
                    "id_number": attendee_id,
                    "role": role,
                    "team": row.get("team", ""),
                    "photo": row.get("photo", ""),
                    "organization": "",
                    "email": row.get("email", ""),
                    "qr_data": f"TEST-ID-{attendee_id or f'MISSING-{row_number:04d}'}",
                }
            )
    return attendees


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as json_file:
        value = json.load(json_file)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _theme_color(theme: dict[str, Any], token: str, role: str) -> str:
    if token == "role":
        return theme["role_colors"].get(role, {}).get(
            "background", theme["colors"]["primary"]
        )
    return theme["colors"].get(token, theme["colors"]["text"])


def _readable_color(
    theme: dict[str, Any],
    token: str,
    role: str,
    background: str | None = None,
) -> str:
    """Use a legible text color when an accent token is too faint on its surface."""
    background = background or theme["colors"]["background"]
    color = _theme_color(theme, token, role)
    if contrast_ratio(color, background) >= MIN_CONTRAST_RATIO:
        return color
    text_color = theme["colors"]["text"]
    if contrast_ratio(text_color, background) >= MIN_CONTRAST_RATIO:
        return text_color
    return max(
        ("#000000", "#FFFFFF"),
        key=lambda candidate: contrast_ratio(candidate, background),
    )


def _badge_text_color(theme: dict[str, Any], role: str, background: str) -> str:
    """Ensure badge labels remain legible, including for unsupported sample roles."""
    candidate = theme.get("role_colors", {}).get(role, {}).get(
        "text", theme["colors"]["background"]
    )
    if contrast_ratio(candidate, background) >= MIN_CONTRAST_RATIO:
        return candidate
    return max(
        ("#000000", "#FFFFFF"),
        key=lambda color: contrast_ratio(color, background),
    )


def _font_family(theme: dict[str, Any], heading: bool = False) -> str:
    font_path = theme.get("fonts", {}).get("heading" if heading else "body", "")
    filename = Path(font_path).stem
    family = filename.split("-")[0] if filename else "sans-serif"
    local_path = FONTS_DIR / Path(font_path).name
    if font_path and not local_path.is_file():
        warnings.warn(
            f"Font file is missing: {local_path}; SVG will use system fallback",
            RuntimeWarning,
            stacklevel=2,
        )
    return family


def _logo_data(source: str, width: int, height: int) -> str | None:
    """Read optional supplied raster logos and preserve their aspect ratio."""
    path = next(
        (
            candidate
            for extension in (".png", ".jpg", ".jpeg")
            if (candidate := LOGOS_DIR / f"{source}{extension}").is_file()
        ),
        None,
    )
    if path is None:
        return None
    try:
        with Image.open(path) as original:
            logo = ImageOps.contain(
                original.convert("RGBA"),
                (max(1, width), max(1, height)),
                method=Image.Resampling.LANCZOS,
            )
    except (OSError, ValueError) as error:
        warnings.warn(
            f"Cannot read logo {path}: {error}; drawing text stand-in instead",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    buffer = io.BytesIO()
    logo.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _photo_data(attendee: dict[str, Any], width: int, height: int) -> str | None:
    photo_name = attendee.get("photo")
    if not photo_name:
        return None
    photo_path = SAMPLE_DATA_DIR / "photos" / Path(str(photo_name)).name
    try:
        with Image.open(photo_path) as source:
            photo = ImageOps.fit(source.convert("RGB"), (width, height))
    except (OSError, ValueError) as error:
        warnings.warn(
            f"Cannot read photo {photo_path}: {error}; drawing placeholder instead",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    buffer = io.BytesIO()
    photo.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _wrap_text(
    value: str,
    width: float,
    max_lines: int,
    measure: Callable[[str], float],
) -> tuple[list[str], bool]:
    """Wrap at measured width, splitting unusually long single words if needed."""
    words = value.split()
    lines: list[str] = []
    current = ""
    overflow = False

    while words:
        word = words.pop(0)
        candidate = f"{current} {word}".strip()
        if measure(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
            if len(lines) >= max_lines:
                overflow = True
                break
        while word and measure(word) > width:
            cut = len(word)
            while cut > 1 and measure(word[:cut]) > width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
            if len(lines) >= max_lines:
                overflow = bool(word or words)
                break
        if len(lines) >= max_lines:
            overflow = overflow or bool(word or words)
            break
        current = word

    if current:
        if len(lines) < max_lines:
            lines.append(current)
        else:
            overflow = True
    if words:
        overflow = True

    if overflow and lines:
        ellipsis = "…"
        last = lines[-1]
        while last and measure(last + ellipsis) > width:
            last = last[:-1]
        lines[-1] = last + ellipsis
    return lines, overflow


def _text_element(
    element: dict[str, Any],
    attendee: dict[str, Any],
    theme: dict[str, Any],
    role: str,
) -> str:
    field = element.get("field", "")
    value = attendee.get(field, "")
    if value is None or str(value).strip() == "":
        return ""

    x, y = float(element.get("x", 0)), float(element.get("y", 0))
    width = float(element.get("w", 0))
    max_lines = max(1, int(element.get("max_lines", 1)))
    min_size = float(element.get("min_font", 7))
    max_size = float(element.get("max_font", min_size))
    color = _readable_color(theme, element.get("color", "text"), role)
    family = _font_family(theme, field in {"full_name", "name"})
    font_points = max_size
    lines: list[str] = []
    while True:
        font_size = font_points * 0.3528
        lines, overflow = _wrap_text(
            str(value),
            width,
            max_lines,
            lambda text: len(text) * font_size * 0.52,
        )
        if not overflow or font_points <= min_size:
            break
        font_points = max(min_size, font_points - 0.5)

    align = element.get("align", "left")
    anchor = {"left": "start", "center": "middle", "right": "end"}.get(align, "start")
    text_x = x if align == "left" else x + width / 2 if align == "center" else x + width
    line_height = font_size * 1.2
    output = []
    for line_index, line in enumerate(lines):
        output.append(
            f'<text x="{text_x:.2f}" y="{y + font_size * 0.9 + line_index * line_height:.2f}" '
            f'font-family="{_escape(family)}, sans-serif" font-size="{font_size:.2f}" '
            f'fill="{_escape(color)}" text-anchor="{anchor}">{_escape(line)}</text>'
        )
    return "".join(output)


def _badge(
    element: dict[str, Any],
    theme: dict[str, Any],
    role: str,
) -> str:
    x, y = float(element["x"]), float(element["y"])
    width, height = float(element["w"]), float(element["h"])
    colors = theme.get("role_colors", {}).get(role, {})
    background = colors.get("background", theme["colors"]["primary"])
    foreground = _badge_text_color(theme, role, background)
    style = theme.get("role_style", {}).get(role, {})
    shape = style.get("badge_shape", element.get("shape", "pill"))
    border = style.get("badge_border", "solid")
    label = style.get("label", role.upper() or "UNKNOWN")
    label_size = min(
        2.8,
        height * 0.32,
        max(1.2, (width - 2) / max(1, len(label) * 0.58)),
    )
    if shape == "shield":
        inset = width * 0.12
        shape_element = (
            f'<path d="M{x:.2f},{y:.2f} H{x + width:.2f} V{y + height * 0.68:.2f} '
            f'L{x + width / 2:.2f},{y + height:.2f} L{x:.2f},{y + height * 0.68:.2f} Z" '
        )
        shape_element += f'fill="{background}"'
        if inset and border == "dashed":
            shape_element += f' stroke="{foreground}" stroke-dasharray="1,0.7"'
        shape_element += "/>"
    else:
        radius = height / 2 if shape == "pill" else 1
        shape_element = (
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
            f'rx="{radius:.2f}" fill="{background}"'
        )
        if border == "dashed":
            shape_element += f' stroke="{foreground}" stroke-dasharray="1,0.7"'
        shape_element += "/>"
    if border == "double":
        shape_element += (
            f'<rect x="{x + 0.7:.2f}" y="{y + 0.7:.2f}" width="{width - 1.4:.2f}" '
            f'height="{height - 1.4:.2f}" rx="{max(0, height / 2 - 0.7):.2f}" '
            f'fill="none" stroke="{foreground}" stroke-width="0.35"/>'
        )
    return (
        f"<g>{shape_element}<text x=\"{x + width / 2:.2f}\" "
        f"y=\"{y + height * 0.64:.2f}\" text-anchor=\"middle\" "
        f"font-family=\"{_escape(_font_family(theme))}, sans-serif\" "
        f"font-size=\"{label_size:.2f}\" font-weight=\"bold\" "
        f"letter-spacing=\"0.15\" fill=\"{_escape(foreground)}\">{_escape(label)}</text></g>"
    )


def _qr_element(
    element: dict[str, Any],
    attendee: dict[str, Any],
    theme: dict[str, Any],
    role: str,
) -> str:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=4)
    qr.add_data(str(attendee.get(element.get("field", "qr_data"), "")))
    qr.make(fit=True)
    matrix = qr.get_matrix()
    count = len(matrix)
    x, y = float(element["x"]), float(element["y"])
    width, height = float(element["w"]), float(element["h"])
    module = min(width, height) / count
    quiet = _theme_color(theme, element.get("background", "background"), role)
    color = _readable_color(theme, element.get("color", "primary"), role, quiet)
    path = []
    for row_index, row in enumerate(matrix):
        for column_index, dark in enumerate(row):
            if dark:
                path.append(
                    f"M{x + column_index * module:.3f},{y + row_index * module:.3f}"
                    f"h{module:.3f}v{module:.3f}h-{module:.3f}z"
                )
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
        f'fill="{_escape(quiet)}"/>'
        f'<path d="{"".join(path)}" fill="{_escape(color)}"/>'
    )


def render_svg(
    layout: dict[str, Any],
    theme: dict[str, Any],
    attendee: dict[str, Any],
) -> str:
    """Render supported layout types to SVG; missing photos use a placeholder."""
    prepared = prepare_layout(layout, attendee)
    role = attendee.get("role", "")
    canvas = layout.get("canvas", {})
    canvas_width = float(canvas.get("width", CANVAS_WIDTH_MM))
    canvas_height = float(canvas.get("height", CANVAS_HEIGHT_MM))
    # Use a larger SVG viewport while preserving the design's millimeter coordinates.
    scale = 8
    width_px, height_px = round(canvas_width * scale), round(canvas_height * scale)
    background = _theme_color(theme, "background", role)
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{height_px}" '
        f'viewBox="0 0 {canvas_width:g} {canvas_height:g}">',
        f'<desc>{_escape(SVG_WARNING)}</desc>',
        f'<rect width="{canvas_width:g}" height="{canvas_height:g}" fill="{_escape(background)}"/>',
        f'<text x="{canvas_width / 2:g}" y="2.2" text-anchor="middle" '
        f'font-family="sans-serif" font-size="1.5" font-weight="bold" '
        f'fill="{_escape(theme["colors"]["accent"])}">{_escape(SVG_WARNING)}</text>',
    ]

    for index, element in enumerate(prepared["elements"]):
        kind = element.get("type")
        x, y = float(element.get("x", 0)), float(element.get("y", 0))
        w, h = float(element.get("w", 0)), float(element.get("h", 0))
        if kind == "rect":
            fill = _theme_color(theme, element.get("fill", "background"), role)
            stroke = element.get("stroke")
            stroke_attr = f' stroke="{_escape(_theme_color(theme, stroke, role))}"' if stroke else ""
            rx = float(element.get("rx", element.get("ry", 0)))
            pieces.append(
                f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                f'rx="{rx:g}" fill="{_escape(fill)}"{stroke_attr}/>'
            )
        elif kind == "line":
            color = _readable_color(theme, element.get("stroke", "text"), role)
            pieces.append(
                f'<line x1="{float(element.get("x1", 0)):g}" y1="{float(element.get("y1", 0)):g}" '
                f'x2="{float(element.get("x2", 0)):g}" y2="{float(element.get("y2", 0)):g}" '
                f'stroke="{_escape(color)}" stroke-width="{float(element.get("stroke_width", 0.3)):g}"/>'
            )
        elif kind == "circle":
            fill = _theme_color(theme, element.get("fill", "accent"), role)
            pieces.append(
                f'<circle cx="{float(element.get("cx", 0)):g}" cy="{float(element.get("cy", 0)):g}" '
                f'r="{float(element.get("r", 0)):g}" fill="{_escape(fill)}"/>'
            )
        elif kind == "text":
            pieces.append(_text_element(element, attendee, theme, role))
        elif kind == "role_badge":
            pieces.append(_badge(element, theme, role))
        elif kind == "qr":
            pieces.append(_qr_element(element, attendee, theme, role))
        elif kind == "photo":
            data = _photo_data(attendee, max(1, round(w * scale)), max(1, round(h * scale)))
            photo_shape = element.get("shape", "rect")
            if photo_shape == "circle":
                clip_shape = (
                    f'<ellipse cx="{x + w / 2:g}" cy="{y + h / 2:g}" '
                    f'rx="{w / 2:g}" ry="{h / 2:g}"/>'
                )
                outline_shape = clip_shape[:-2] + ' fill="none"/>'
            elif photo_shape == "rounded_rect":
                radius = min(w, h) * 0.12
                clip_shape = (
                    f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                    f'rx="{radius:g}" ry="{radius:g}"/>'
                )
                outline_shape = clip_shape[:-2] + ' fill="none"/>'
            else:
                clip_shape = (
                    f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}"/>'
                )
                outline_shape = clip_shape[:-2] + ' fill="none"/>'
            pieces.append(
                f'<defs><clipPath id="photo-clip-{index}">'
                f'{clip_shape}</clipPath></defs>'
            )
            if data:
                pieces.append(
                    f'<image x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                    f'href="data:image/png;base64,{data}" preserveAspectRatio="xMidYMid slice" '
                    f'clip-path="url(#photo-clip-{index})"/>'
                )
            else:
                fallback = _theme_color(theme, "secondary", role)
                fallback_shape = (
                    clip_shape[:-2]
                    + f' fill="{_escape(fallback)}" '
                    + f'clip-path="url(#photo-clip-{index})"/>'
                )
                pieces.append(
                    fallback_shape
                )
                pieces.append(
                    f'<text x="{x + w / 2:g}" y="{y + h / 2:g}" text-anchor="middle" '
                    f'font-family="sans-serif" font-size="{min(2.5, h * 0.12):g}" '
                    f'fill="{_escape(_readable_color(theme, "text", role, fallback))}" '
                    f'clip-path="url(#photo-clip-{index})">NO PHOTO</text>'
                )
            if element.get("border_color"):
                pieces.append(
                    f'{outline_shape[:-2]} stroke="{_escape(_theme_color(theme, element["border_color"], role))}" '
                    f'stroke-width="{float(element.get("border_width", 0.3)):g}"/>'
                )
        elif kind == "logo":
            source = str(element.get("src", ""))
            data = _logo_data(source, round(w * scale), round(h * scale))
            if data:
                pieces.append(
                    f'<image x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                    f'href="data:image/png;base64,{data}" '
                    'preserveAspectRatio="xMidYMid meet"/>'
                )
            else:
                logo_text = "ACM NIT SURAT" if source == "acm_nit_surat" else "SVNIT"
                logo_color = _readable_color(theme, "primary", role)
                pieces.append(
                    f'<text x="{x + w / 2:g}" y="{y + h / 2:g}" text-anchor="middle" '
                    f'dominant-baseline="middle" font-family="sans-serif" '
                    f'font-size="{min(2.5, h * 0.35):g}" font-weight="bold" '
                    f'fill="{_escape(logo_color)}">{logo_text}</text>'
                )
        elif kind == "svg_asset":
            pieces.append(
                f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                f'fill="none" stroke="{_escape(theme["colors"]["accent"])}" '
                f'stroke-dasharray="1,1"/>'
            )

    pieces.append("</svg>")
    return "".join(pieces)


def render_png(
    layout: dict[str, Any],
    theme: dict[str, Any],
    attendee: dict[str, Any],
    output_width: int | None = None,
) -> bytes:
    """Rasterize with CairoSVG, falling back to Pillow if native Cairo is absent."""
    svg = render_svg(layout, theme, attendee).encode("utf-8")
    try:
        import cairosvg

        kwargs = {"bytestring": svg}
        if output_width is not None:
            kwargs["output_width"] = output_width
        return cairosvg.svg2png(**kwargs)
    except OSError as error:
        if "no library called" not in str(error) and "cannot load library" not in str(error):
            raise
        warnings.warn(
            "CairoSVG's native Cairo library is unavailable; using Pillow PNG fallback",
            RuntimeWarning,
            stacklevel=2,
        )
        return _render_pillow_png(layout, theme, attendee, output_width)


def _render_pillow_png(
    layout: dict[str, Any],
    theme: dict[str, Any],
    attendee: dict[str, Any],
    output_width: int | None,
) -> bytes:
    """Render the supported card elements directly with Pillow."""
    canvas = layout.get("canvas", {})
    canvas_width = float(canvas.get("width", CANVAS_WIDTH_MM))
    canvas_height = float(canvas.get("height", CANVAS_HEIGHT_MM))
    output_width = output_width or round(canvas_width * 8)
    scale = output_width / canvas_width
    output_height = round(canvas_height * scale)
    role = attendee.get("role", "")
    prepared = prepare_layout(layout, attendee)
    image = Image.new(
        "RGB",
        (output_width, output_height),
        _theme_color(theme, "background", role),
    )
    draw = ImageDraw.Draw(image)

    def px(value: float) -> int:
        return round(value * scale)

    def font_for(font_size: float, heading: bool = False) -> ImageFont.ImageFont:
        font_name = Path(
            theme.get("fonts", {}).get("heading" if heading else "body", "")
        ).name
        font_path = FONTS_DIR / font_name
        if not font_path.is_file():
            fallback_name = "arialbd.ttf" if heading else "arial.ttf"
            windows_font = Path("C:/Windows/Fonts") / fallback_name
            font_path = windows_font if windows_font.is_file() else font_path
        try:
            return ImageFont.truetype(str(font_path), max(1, px(font_size * 0.3528)))
        except OSError:
            return ImageFont.load_default()

    for element in prepared["elements"]:
        kind = element.get("type")
        x, y = float(element.get("x", 0)), float(element.get("y", 0))
        width, height = float(element.get("w", 0)), float(element.get("h", 0))
        box = (px(x), px(y), px(x + width), px(y + height))

        if kind == "rect":
            fill = _theme_color(theme, element.get("fill", "background"), role)
            draw.rounded_rectangle(
                box,
                radius=px(float(element.get("rx", element.get("ry", 0)))),
                fill=fill,
            )
        elif kind == "line":
            draw.line(
                (
                    px(float(element["x1"])),
                    px(float(element["y1"])),
                    px(float(element["x2"])),
                    px(float(element["y2"])),
                ),
                fill=_readable_color(theme, element.get("stroke", "text"), role),
                width=max(1, px(float(element.get("stroke_width", 0.3)))),
            )
        elif kind == "circle":
            radius = float(element["r"])
            center_x, center_y = float(element["cx"]), float(element["cy"])
            draw.ellipse(
                (px(center_x - radius), px(center_y - radius),
                 px(center_x + radius), px(center_y + radius)),
                fill=_theme_color(theme, element.get("fill", "accent"), role),
            )
        elif kind == "text":
            value = attendee.get(element.get("field", ""), "")
            if value is None or not str(value).strip():
                continue
            color = _readable_color(theme, element.get("color", "text"), role)
            max_lines = max(1, int(element.get("max_lines", 1)))
            min_font = float(element.get("min_font", 7))
            max_font = float(element.get("max_font", min_font))
            font_size = max_font
            font = font_for(font_size, element.get("field") == "full_name")
            max_width = px(width)
            lines, overflow = _wrap_text(
                str(value),
                max_width,
                max_lines,
                lambda text: draw.textlength(text, font=font),
            )
            while overflow and font_size > min_font:
                font_size = max(min_font, font_size - 0.5)
                font = font_for(font_size, element.get("field") == "full_name")
                lines, overflow = _wrap_text(
                    str(value),
                    max_width,
                    max_lines,
                    lambda text: draw.textlength(text, font=font),
                )
            align = element.get("align", "left")
            top = px(y)
            for line in lines:
                draw.text(
                    (px(x + width / 2) if align == "center" else
                     px(x + width) if align == "right" else px(x), top),
                    line,
                    font=font,
                    fill=color,
                    anchor={"left": "lt", "center": "mt", "right": "rt"}.get(align, "lt"),
                )
                top += max(1, round(font_size * 0.46 * scale))
        elif kind == "role_badge":
            colors = theme.get("role_colors", {}).get(role, {})
            fill = colors.get("background", theme["colors"]["primary"])
            foreground = _badge_text_color(theme, role, fill)
            style = theme.get("role_style", {}).get(role, {})
            shape = style.get("badge_shape", element.get("shape", "pill"))
            border = style.get("badge_border", "solid")
            label = style.get("label", role.upper() or "UNKNOWN")
            if shape == "shield":
                points = [
                    (px(x), px(y)), (px(x + width), px(y)),
                    (px(x + width), px(y + height * 0.68)),
                    (px(x + width / 2), px(y + height)),
                    (px(x), px(y + height * 0.68)),
                ]
                draw.polygon(points, fill=fill)
                if border == "double":
                    draw.line(points + [points[0]], fill=foreground, width=max(1, px(0.35)))
            else:
                radius = px(height / 2) if shape == "pill" else px(1)
                draw.rounded_rectangle(box, radius=radius, fill=fill)
                if border == "double":
                    inset = px(0.7)
                    draw.rounded_rectangle(
                        (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset),
                        radius=max(0, radius - inset),
                        outline=foreground,
                        width=max(1, px(0.35)),
                    )
                elif border == "dashed":
                    for dash_x in range(box[0], box[2], max(2, px(1.7))):
                        draw.line(
                            (dash_x, box[1], min(dash_x + px(0.8), box[2]), box[1]),
                            fill=foreground,
                            width=max(1, px(0.3)),
                        )
            label_size = 7.0
            label_font = font_for(label_size)
            while (
                label_size > 3.0
                and draw.textlength(label, font=label_font) > px(width * 0.88)
            ):
                label_size -= 0.5
                label_font = font_for(label_size)
            draw.text(
                (px(x + width / 2), px(y + height / 2)),
                label,
                font=label_font,
                fill=foreground,
                anchor="mm",
            )
        elif kind == "qr":
            qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=4)
            qr.add_data(str(attendee.get(element.get("field", "qr_data"), "")))
            qr.make(fit=True)
            matrix = qr.get_matrix()
            qr_size = min(px(width), px(height))
            qr_image = Image.new(
                "RGB",
                (qr_size, qr_size),
                _theme_color(theme, element.get("background", "background"), role),
            )
            qr_draw = ImageDraw.Draw(qr_image)
            module = qr_size / len(matrix)
            qr_color = _readable_color(
                theme,
                element.get("color", "primary"),
                role,
                _theme_color(theme, element.get("background", "background"), role),
            )
            for row_index, row in enumerate(matrix):
                for column_index, dark in enumerate(row):
                    if dark:
                        qr_draw.rectangle(
                            (
                                round(column_index * module),
                                round(row_index * module),
                                round((column_index + 1) * module),
                                round((row_index + 1) * module),
                            ),
                            fill=qr_color,
                        )
            image.paste(qr_image, (px(x), px(y)))
        elif kind == "photo":
            photo_data = _photo_data(attendee, max(1, px(width)), max(1, px(height)))
            if photo_data:
                photo = Image.open(io.BytesIO(base64.b64decode(photo_data))).convert("RGB")
            else:
                photo = Image.new(
                    "RGB",
                    (max(1, px(width)), max(1, px(height))),
                    _theme_color(theme, "secondary", role),
                )
                ImageDraw.Draw(photo).text(
                    (photo.width // 2, photo.height // 2),
                    "NO PHOTO",
                    fill=theme["colors"]["background"],
                    font=font_for(6),
                    anchor="mm",
                )
            mask = Image.new("L", photo.size, 0)
            mask_draw = ImageDraw.Draw(mask)
            shape = element.get("shape", "rect")
            if shape == "circle":
                mask_draw.ellipse((0, 0, photo.width - 1, photo.height - 1), fill=255)
            elif shape == "rounded_rect":
                mask_draw.rounded_rectangle(
                    (0, 0, photo.width - 1, photo.height - 1),
                    radius=max(1, round(min(photo.size) * 0.12)),
                    fill=255,
                )
            else:
                mask_draw.rectangle((0, 0, photo.width - 1, photo.height - 1), fill=255)
            image.paste(photo, (px(x), px(y)), mask)
            if element.get("border_color"):
                outline = Image.new("L", photo.size, 0)
                outline_draw = ImageDraw.Draw(outline)
                if shape == "circle":
                    outline_draw.ellipse((0, 0, photo.width - 1, photo.height - 1), outline=255)
                elif shape == "rounded_rect":
                    outline_draw.rounded_rectangle(
                        (0, 0, photo.width - 1, photo.height - 1),
                        radius=max(1, round(min(photo.size) * 0.12)),
                        outline=255,
                    )
                else:
                    outline_draw.rectangle((0, 0, photo.width - 1, photo.height - 1), outline=255)
                border_image = Image.new(
                    "RGB",
                    photo.size,
                    _theme_color(theme, element["border_color"], role),
                )
                image.paste(border_image, (px(x), px(y)), outline)
            photo.close()
        elif kind == "logo":
            source = str(element.get("src", ""))
            data = _logo_data(source, px(width), px(height))
            if data:
                logo = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGBA")
                image.paste(
                    logo,
                    (
                        px(x + width / 2) - logo.width // 2,
                        px(y + height / 2) - logo.height // 2,
                    ),
                    logo,
                )
                logo.close()
            else:
                label = "ACM NIT SURAT" if source == "acm_nit_surat" else "SVNIT"
                draw.text(
                    (px(x + width / 2), px(y + height / 2)),
                    label,
                    font=font_for(6, heading=True),
                    fill=_readable_color(theme, "primary", role),
                    anchor="mm",
                )
        elif kind == "svg_asset":
            draw.rectangle(box, outline=theme["colors"]["accent"], width=max(1, px(0.3)))
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    image.close()
    return output.getvalue()


def load_layout_theme(layout_name: str, theme_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load one JSON layout and theme by filename stem."""
    layout = _read_json(LAYOUTS_DIR / f"{layout_name}.json")
    theme = _read_json(THEMES_DIR / f"{theme_name}.json")
    return layout, theme
