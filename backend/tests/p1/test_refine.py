"""Unit tests for Natural Language Design Spec refinement (Phase 2).

Verifies:
- Allowlist strictly forbids tampering with attendee facts, event metadata, or institutional logos.
- Deterministic heuristic fallbacks produce correct patch operations without requiring an LLM.
- The POST /spec/refine endpoint safely parses prompts and updates specs.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.api.models import RefineRequest
from app.main import app
from app.refine.nl_to_patch import nl_to_patch, validate_patch_op
from app.spec.schema import DesignSpec


from app.generator.library import get_layout, get_theme
from app.spec.loader import merge_design_spec


@pytest.fixture
def sample_spec() -> DesignSpec:
    return merge_design_spec(get_layout("classic"), get_theme("clean_light"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_validate_patch_op_forbids_tampering():
    """Verify that participant facts, event details, and logo removals are strictly blocked."""
    # Attempt to tamper with event details
    assert not validate_patch_op({"op": "set", "path": "event.event_name", "value": "Unauthorized Event"})
    assert not validate_patch_op({"op": "set", "path": "event.dates", "value": "Jan 1, 2099"})
    assert not validate_patch_op({"op": "set", "path": "event.venue", "value": "Nowhere"})

    # Attempt to tamper with attendee identity
    assert not validate_patch_op({"op": "set", "path": "person.name", "value": "Attacker"})
    assert not validate_patch_op({"op": "set", "path": "attendee_email", "value": "hack@evil.com"})
    assert not validate_patch_op({"op": "set", "path": "participant_name", "value": "Bob"})

    # Attempt to remove logos
    assert not validate_patch_op({"op": "remove", "path": "brand.logos.acm_nitsurat", "value": None})
    assert not validate_patch_op({"op": "remove", "path": "brand.logos.svnit", "value": None})
    assert not validate_patch_op({"op": "remove", "path": "elements.logo_acm", "value": None})
    assert not validate_patch_op({"op": "remove", "path": "elements.logo_svnit", "value": None})

    # Attempt to modify schema version or page geometry
    assert not validate_patch_op({"op": "set", "path": "schema_version", "value": "99.0"})
    assert not validate_patch_op({"op": "set", "path": "page.width_mm", "value": 100})


def test_validate_patch_op_allows_aesthetic_modifications():
    """Verify that theme colors, typography, and element visual attributes are permitted."""
    assert validate_patch_op({"op": "set", "path": "theme.colors.background", "value": "#111111"})
    assert validate_patch_op({"op": "set", "path": "theme.colors.primary", "value": "#3B82F6"})
    assert validate_patch_op({"op": "set", "path": "theme.role_colors.organizer", "value": "#D9480F"})
    assert validate_patch_op({"op": "set", "path": "theme.fonts.heading", "value": "Poppins"})
    assert validate_patch_op({"op": "set", "path": "elements.photo.shape", "value": "circle"})
    assert validate_patch_op({"op": "set", "path": "elements.name.max_font", "value": 16})
    assert validate_patch_op({"op": "set", "path": "elements.name.align", "value": "center"})


from app.refine.nl_to_patch import _deterministic_nlp_refine, nl_to_patch, validate_patch_op


def test_deterministic_nlp_refinements(sample_spec: DesignSpec):
    """Test deterministic rule-based refinement for photo shape, typography, theme, and colors."""
    # 1. Photo shape
    ops = _deterministic_nlp_refine("Please make the attendee photo a circle", sample_spec)
    assert any(op["path"] == "elements.photo.shape" and op["value"] == "circle" for op in ops)

    # 2. Typography prominence
    ops = _deterministic_nlp_refine("Make the name bigger and more prominent", sample_spec)
    assert any(op["path"] == "elements.name.max_font" and op["value"] == 16 for op in ops)
    assert any(op["path"] == "elements.name.bold" and op["value"] is True for op in ops)

    # 3. Theme mode
    ops = _deterministic_nlp_refine("Switch to dark tech theme with high contrast", sample_spec)
    assert any(op["path"] == "theme_name" and op["value"] == "dark_tech" for op in ops)
    assert any(op["path"] == "theme.colors.background" and op["value"] == "#0B1220" for op in ops)

    # 4. Heading font
    ops = _deterministic_nlp_refine("Use Poppins for the heading font", sample_spec)
    assert any(op["path"] == "theme.fonts.heading" and op["value"] == "Poppins" for op in ops)


def test_refine_api_endpoint(client: TestClient, sample_spec: DesignSpec):
    """Verify POST /spec/refine produces a valid updated spec and patch summary."""
    payload = {
        "spec": sample_spec.model_dump(),
        "prompt": "Make the photo circular and center the name",
    }
    response = client.post("/spec/refine", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "spec" in data
    assert "ops" in data
    assert "summary" in data
    assert len(data["ops"]) >= 1

    # Check updated spec reflects the changes
    updated_elements = {
        (elem.get("id") or elem.get("field") or elem.get("type")): elem
        for elem in data["spec"]["elements"]
    }
    assert updated_elements["photo"]["shape"] == "circle"
    assert updated_elements["name"]["align"] == "center"


def test_refine_api_endpoint_empty_prompt(client: TestClient, sample_spec: DesignSpec):
    """Verify POST /spec/refine handles prompts with no visual changes gracefully."""
    payload = {
        "spec": sample_spec.model_dump(),
        "prompt": "This is random text with no instructions",
    }
    response = client.post("/spec/refine", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["ops"]) == 0
    assert "unchanged" in data["summary"].lower()
