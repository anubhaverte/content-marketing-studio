"""Tests for rendering canonical layouts and themes into self-contained SVG."""

from pathlib import Path
from xml.etree import ElementTree

from app.spec.loader import load_layout, load_theme, merge_design_spec
from app.spec.schema import CircleEl, Person, QrEl, SvgAssetEl
from app.render.svg_builder import build_svg


BACKEND = Path(__file__).resolve().parents[2]
LAYOUTS = BACKEND / "app" / "templates" / "layouts"
THEMES = BACKEND / "app" / "templates" / "themes"


def _sample_spec():
    layout = load_layout(LAYOUTS / "classic.json")
    theme = load_theme(THEMES / "clean_light.json")
    return merge_design_spec(layout, theme)


def test_svg_builder_embeds_fonts_and_both_aspect_preserving_logos():
    spec = _sample_spec()
    person = Person(name="Jane Doe", role="participant", id="P-001")

    svg = build_svg(spec, person)
    root = ElementTree.fromstring(svg)

    assert root.get("width") == "60mm"
    assert root.get("height") == "92mm"
    assert root.get("viewBox") == "0 0 60 92"
    assert "Jane Doe" in svg
    assert svg.count("href=\"data:image/svg+xml;base64,") == 2
    assert "preserveAspectRatio=\"xMidYMid meet\"" in svg
    assert "data:font/ttf;base64," in svg
    assert "font-weight:700" in svg


def test_svg_builder_is_deterministic_and_uses_real_qr_payload():
    spec = _sample_spec()
    spec.elements.append(
        QrEl(type="qr", field="qr_url", x=40, y=66, w=14, h=14)
    )
    person = Person(
        name="Jane Doe",
        role="participant",
        qr_url="https://example.test/verify/P-001",
    )

    first = build_svg(spec, person)
    second = build_svg(spec, person)

    assert first == second
    assert "data-qr-payload=\"https://example.test/verify/P-001\"" in first
    assert "<path" in first
    assert 'id="debug-guides"' not in first
    assert 'id="guide-safe"' in build_svg(spec, person, debug_guides=True)


def test_svg_builder_renders_circle_and_embedded_svg_asset(tmp_path, monkeypatch):
    asset = tmp_path / "motif.svg"
    asset.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<circle cx="5" cy="5" r="4"/></svg>',
        encoding="utf-8",
    )
    monkeypatch.setattr("app.render.svg_builder._svg_asset_path", lambda _src: asset)
    spec = _sample_spec()
    spec.elements.extend([
        CircleEl(type="circle", id="test-disc", cx=50, cy=50, r=3, fill="accent"),
        SvgAssetEl(
            type="svg_asset",
            id="test-motif",
            src="motif.svg",
            x=2,
            y=50,
            w=6,
            h=6,
        ),
    ])

    svg = build_svg(spec, Person(name="Jane Doe"))

    assert 'id="test-disc"' in svg
    assert 'id="test-motif"' in svg
    assert 'href="data:image/svg+xml;base64,' in svg


def test_svg_builder_loads_photo_from_sample_data_photos():
    svg = build_svg(
        _sample_spec(),
        Person(name="Jane Doe", photo="photos/tall.png"),
    )

    assert 'data-photo-status="embedded"' in svg
    assert 'data-photo-status="fallback"' not in svg
