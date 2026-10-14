"""Focused tests for automatic rendered-card QA."""

from __future__ import annotations

import warnings
from itertools import product
from xml.etree import ElementTree

import pytest
from PIL import Image

from qa import checks
from qa.checks import Issue, run_qa
from qa.report import format_issues, issues_to_dict
from render import spec_adapter
from render.loaders import load_layout, load_theme
from render.renderer import render_card


@pytest.fixture
def card():
    """Return a standard spec, sample person, layout, theme, and SVG."""
    spec = spec_adapter.load_design_spec()
    people = spec_adapter.load_people()
    person = people[1]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        svg = render_card(spec, person)
    return spec, person, svg, load_layout("classic"), load_theme("blue")


def _issues_for(card, *, person=None, svg=None, layout=None, theme=None):
    """Run QA with optional changed inputs."""
    spec, original_person, original_svg, original_layout, original_theme = card
    return run_qa(
        spec,
        original_person if person is None else person,
        original_svg if svg is None else svg,
        original_layout if layout is None else layout,
        original_theme if theme is None else theme,
    )


def _find(issues: list[Issue], check: str) -> Issue:
    """Return a matching issue or fail the test."""
    return next(issue for issue in issues if issue.check == check)


def test_text_overflow_detects_text_box_that_is_too_small(card):
    layout = {**card[3], "elements": [dict(item) for item in card[3]["elements"]]}
    name = next(item for item in layout["elements"] if item.get("id") == "person-name")
    name["max_width"] = 1
    issue = _find(_issues_for(card, layout=layout), "text_overflow")
    assert issue.severity == "error"
    assert "person-name" in issue.message


@pytest.mark.parametrize("layout_name", ["classic", "split"])
@pytest.mark.parametrize("name", ["Élodie Núñez", "Å Ö Ç Ý ñ g y"])
def test_accented_and_tall_glyphs_stay_inside_name_box(card, layout_name, name):
    spec, person, _, _, _ = card
    person = spec_adapter.Person({**person._data, "name": name}, person._source_file)
    spec = spec_adapter.with_choices(spec, layout=layout_name)
    layout = load_layout(layout_name)
    theme = load_theme("blue")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        svg = render_card(spec, person)
    errors = [
        issue
        for issue in run_qa(spec, person, svg, layout, theme)
        if issue.check == "text_overflow" and issue.severity == "error"
    ]
    assert errors == []


def test_logo_aspect_ratio_detects_stretched_source(card, tmp_path, monkeypatch):
    logo = tmp_path / "acm.png"
    Image.new("RGB", (20, 10), "white").save(logo)
    monkeypatch.setattr(checks, "_find_asset", lambda name: logo if name == "acm" else None)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<image id="logo-acm" data-logo-status="embedded" width="10" height="10"/>'
        "</svg>"
    )
    issue = _find(_issues_for(card, svg=svg), "logo_aspect_ratio")
    assert issue.severity == "error"
    assert "ratio" in issue.message


def test_contrast_detects_theme_color_pair_below_threshold(card):
    theme = {**card[4], "colors": dict(card[4]["colors"])}
    theme["colors"]["text_on_primary"] = theme["colors"]["primary"]
    issue = _find(_issues_for(card, theme=theme), "contrast")
    assert issue.severity == "error"
    assert ":1 contrast" in issue.message
    assert "event-name" in issue.message
    assert "#" in issue.message


def test_missing_photo_initials_have_theme_contrast_for_every_role_and_design(card):
    spec, source_person, _, _, _ = card
    for role, theme_name, layout_name in product(
        spec_adapter.ROLES, ("blue", "dark"), ("classic", "split")
    ):
        selected_spec = spec_adapter.with_choices(
            spec, layout=layout_name, theme=theme_name
        )
        layout = load_layout(layout_name)
        theme = load_theme(theme_name)
        person = spec_adapter.Person(
            {**source_person._data, "role": role, "photo": None},
            source_person._source_file,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            svg = render_card(selected_spec, person)
        root = ElementTree.fromstring(svg)
        text = root.find(".//*[@id='person-photo-initials']")
        assert text is not None, (role, theme_name, layout_name)
        foreground = text.get("fill")
        photo = root.find(".//*[@id='person-photo']")
        assert photo is not None
        background = next(child.get("fill") for child in photo if child.tag.endswith("rect"))
        assert checks._contrast_ratio(foreground, background) >= 4.5
        assert not [
            issue
            for issue in run_qa(selected_spec, person, svg, layout, theme)
            if issue.check == "contrast" and issue.severity == "error"
        ]


def test_overlap_detects_intersecting_layout_elements(card):
    layout = {**card[3], "elements": list(card[3]["elements"])}
    layout["elements"].append({
        "id": "collision",
        "type": "photo",
        "position": {"x": 21, "y": 34},
        "size": {"width": 4, "height": 4},
    })
    issue = _find(_issues_for(card, layout=layout), "overlap")
    assert issue.severity == "error"
    assert "collision" in issue.message


def test_empty_fields_reports_empty_name_and_fallback(card):
    spec, person, svg, layout, theme = card
    missing_name = spec_adapter.Person(
        {**person._data, "name": ""}, person._source_file
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fallback_svg = render_card(spec, missing_name)
    issue = _find(_issues_for(card, person=missing_name, svg=fallback_svg), "empty_fields")
    assert issue.severity == "error"
    assert "fallback was used" in issue.message


def test_data_match_detects_changed_card_text(card):
    svg = card[2].replace(">Cher</tspan>", ">Not Cher</tspan>")
    issue = _find(_issues_for(card, svg=svg), "data_match")
    assert issue.severity == "error"
    assert "name" in issue.message


def test_resolution_detects_png_exported_at_wrong_size(card, monkeypatch):
    import cairosvg

    def wrong_size(*, bytestring, write_to, dpi):
        Image.new("RGB", (12, 12), "white").save(write_to)

    monkeypatch.setattr(cairosvg, "svg2png", wrong_size)
    issue = _find(_issues_for(card), "resolution")
    assert issue.severity == "error"
    assert "12 x 12 px" in issue.message
    assert "709 x 1087 px" in issue.message


def test_good_card_has_no_errors(card):
    issues = _issues_for(card)
    assert not [issue for issue in issues if issue.severity == "error"]
    assert all(issue.severity in {"error", "warning"} for issue in issues)


def test_exception_in_one_check_does_not_stop_other_checks(card, monkeypatch):
    def broken_check(*args, **kwargs):
        raise RuntimeError("intentional test failure")

    original_resolution_check = checks._check_resolution
    resolution_ran = False

    def tracked_resolution_check(*args, **kwargs):
        nonlocal resolution_ran
        resolution_ran = True
        return original_resolution_check(*args, **kwargs)

    monkeypatch.setattr(checks, "_check_logo_aspect_ratio", broken_check)
    monkeypatch.setattr(checks, "_check_resolution", tracked_resolution_check)
    issues = _issues_for(card)
    failure = _find(issues, "logo_aspect_ratio")
    assert failure.severity == "error"
    assert "intentional test failure" in failure.message
    assert any(issue.check == "empty_fields" for issue in issues)
    assert resolution_ran


def test_issue_reporting_is_readable_and_json_friendly():
    issue = Issue("contrast", "error", "person-001", "Contrast is 2.0:1.")
    assert "ERROR: contrast (person person-001)" in format_issues([issue])
    assert issues_to_dict([issue]) == [{
        "check": "contrast",
        "severity": "error",
        "person_id": "person-001",
        "message": "Contrast is 2.0:1.",
    }]
