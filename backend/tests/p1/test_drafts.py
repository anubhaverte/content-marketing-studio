"""Tests for deterministic candidate draft generation and scoring."""
import pytest
from fastapi.testclient import TestClient

from app.brief.schema import Brief
from app.generator.drafts import generate_drafts, score_combination
from app.generator.library import get_layout, get_theme
from app.main import app
from app.spec.schema import DesignSpec, EventInfo, Layout, PageSpec, RectEl, Theme, ThemeColors, ThemeFonts

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures creating in-memory synthetic catalogs for diversity testing
# ---------------------------------------------------------------------------

@pytest.fixture
def multi_catalog_mock(monkeypatch):
    """Mocks library list_layouts, list_themes, get_layout, get_theme with 3 layouts and 3 themes."""
    layouts = {
        "classic": Layout(
            name="classic",
            page=PageSpec(),
            elements=[
                RectEl(type="rect", id="bg", x=0, y=0, w=60, h=92, fill="background"),
            ],
        ),
        "minimal": Layout(
            name="minimal",
            page=PageSpec(),
            elements=[
                RectEl(type="rect", id="bg", x=0, y=0, w=60, h=92, fill="background"),
            ],
        ),
        "modern_split": Layout(
            name="modern_split",
            page=PageSpec(),
            elements=[
                RectEl(type="rect", id="bg", x=0, y=0, w=60, h=92, fill="background"),
            ],
        ),
    }

    themes = {
        "clean_light": Theme(
            name="clean_light",
            colors=ThemeColors(
                background="#FFFFFF",
                primary="#1F6FEB",
                secondary="#EAF1FD",
                accent="#38BDF8",
                text="#0B1220",
            ),
            fonts=ThemeFonts(heading="Poppins", body="Inter"),
            role_colors={"participant": "#1F6FEB", "organizer": "#D9480F", "mentor": "#2F9E44"},
        ),
        "dark_tech": Theme(
            name="dark_tech",
            colors=ThemeColors(
                background="#0B1220",
                primary="#0C8599",
                secondary="#1098AD",
                accent="#66D9E8",
                text="#FFFFFF",
            ),
            fonts=ThemeFonts(heading="JetBrains Mono", body="Roboto"),
            role_colors={"participant": "#0C8599", "organizer": "#D9480F", "mentor": "#2F9E44"},
        ),
        "bold_gradient": Theme(
            name="bold_gradient",
            colors=ThemeColors(
                background="#FAFAFA",
                primary="#D9480F",
                secondary="#FFE8CC",
                accent="#E8590C",
                text="#1A1A1A",
            ),
            fonts=ThemeFonts(heading="Outfit", body="Inter"),
            role_colors={"participant": "#D9480F", "organizer": "#2F9E44", "mentor": "#7950F2"},
        ),
    }

    monkeypatch.setattr("app.generator.drafts.list_layouts", lambda: sorted(layouts.keys()))
    monkeypatch.setattr("app.generator.drafts.list_themes", lambda: sorted(themes.keys()))
    monkeypatch.setattr("app.generator.drafts.get_layout", lambda name: layouts[name])
    monkeypatch.setattr("app.generator.drafts.get_theme", lambda name: themes[name])

    return layouts, themes


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_drafts_generation_produces_three_distinct_candidates(multi_catalog_mock):
    """When catalog contains >= 3 layouts and themes, exactly 3 distinct combinations are returned."""
    brief = Brief(design_type="id_card", event_name="SVNIT CodeFest 2026", style_hint="clean")
    drafts, is_mock = generate_drafts(brief=brief, count=3, allow_theme_variations=False)

    assert len(drafts) == 3
    assert is_mock is False

    # Check distinct combinations (no duplicates)
    combos = [(d.layout_name, d.theme_name) for d in drafts]
    assert len(set(combos)) == 3
    # Check that all 3 are valid DesignSpecs
    for d in drafts:
        assert isinstance(d, DesignSpec)
        assert d.event.event_name == "SVNIT CodeFest 2026"


def test_drafts_deterministic_ordering_across_repeated_calls(multi_catalog_mock):
    """Consecutive calls with the same input produce identical draft combinations."""
    brief = Brief(design_type="id_card", event_name="Repeat Test", style_hint="techy")
    drafts_1, _ = generate_drafts(brief=brief, count=3)
    drafts_2, _ = generate_drafts(brief=brief, count=3)

    assert [(d.layout_name, d.theme_name) for d in drafts_1] == [(d.layout_name, d.theme_name) for d in drafts_2]
    assert [d.theme.colors.primary for d in drafts_1] == [d.theme.colors.primary for d in drafts_2]


def test_style_hints_influence_ranking(multi_catalog_mock):
    """Style hint 'dark_tech' causes dark_tech theme and modern layout to rank first."""
    brief_tech = Brief(design_type="id_card", style_hint="dark")
    drafts_tech, _ = generate_drafts(brief=brief_tech, count=3)
    # The top candidate should match the 'dark' theme
    assert drafts_tech[0].theme_name == "dark_tech"

    brief_clean = Brief(design_type="id_card", style_hint="minimal")
    drafts_clean, _ = generate_drafts(brief=brief_clean, count=3)
    assert drafts_clean[0].layout_name == "minimal" or drafts_clean[0].theme_name == "clean_light"


def test_no_silent_duplication_when_catalog_is_limited():
    """When catalog has fewer combinations than count and allow_theme_variations=False, returns exact catalog count."""
    # Current disk catalog has 1 layout ('classic') and 1 theme ('clean_light')
    drafts, is_mock = generate_drafts(count=3, allow_theme_variations=False)
    # Should not duplicate to reach 3
    assert len(drafts) == 1
    assert drafts[0].layout_name == "classic"
    assert drafts[0].theme_name == "clean_light"
    assert is_mock is False


def test_theme_variations_fallback_when_allowed_and_catalog_limited():
    """When allow_theme_variations=True and catalog has only 1 combo, fills to count with varied colors and marks mock=True."""
    drafts, is_mock = generate_drafts(count=3, allow_theme_variations=True)
    assert len(drafts) == 3
    assert is_mock is True
    # The primary colors across the 3 drafts must differ
    primaries = [d.theme.colors.primary for d in drafts]
    assert len(set(primaries)) == 3


def test_preserves_brief_and_event_constraints():
    """Event constraints from brief are faithfully set on DesignSpec without hallucinating unprovided fields."""
    brief = Brief(
        design_type="id_card",
        event_name="ACM Summit",
        venue="NIT Surat",
        dates="Nov 20-22",
        tagline=None,  # Unset
    )
    drafts, _ = generate_drafts(brief=brief, count=1)
    spec = drafts[0]
    assert spec.event.event_name == "ACM Summit"
    assert spec.event.venue == "NIT Surat"
    assert spec.event.dates == "Nov 20-22"
    assert spec.event.tagline is None  # Never fabricated


def test_missing_or_empty_catalog_returns_empty_list(monkeypatch):
    """When no layouts or themes exist, returns empty list without crashing."""
    monkeypatch.setattr("app.generator.drafts.list_layouts", lambda: [])
    monkeypatch.setattr("app.generator.drafts.list_themes", lambda: [])
    drafts, is_mock = generate_drafts(count=3)
    assert drafts == []
    assert is_mock is True


# ---------------------------------------------------------------------------
# API integration tests: POST /drafts
# ---------------------------------------------------------------------------

def test_api_drafts_endpoint_with_explicit_mock_false():
    """POST /drafts?mock=false returns real distinct catalog candidates."""
    payload = {
        "brief": {"design_type": "id_card", "event_name": "API Test"},
        "count": 3,
    }
    response = client.post("/drafts?mock=false", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is False
    # With 1 catalog pair on disk and no mock variations allowed, returns 1
    assert len(data["drafts"]) == 1
    assert data["drafts"][0]["layout_name"] == "classic"


def test_api_drafts_endpoint_with_mock_true():
    """POST /drafts?mock=true returns requested count with mock=True."""
    payload = {
        "brief": {"design_type": "id_card", "event_name": "API Mock Test"},
        "count": 3,
    }
    response = client.post("/drafts?mock=true", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is True
    assert len(data["drafts"]) == 3
