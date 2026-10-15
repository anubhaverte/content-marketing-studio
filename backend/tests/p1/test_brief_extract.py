"""Tests for AI Brief extraction, missing information detection, and question generation."""
import json
import pytest
from fastapi.testclient import TestClient

from app.api.models import BriefRequest, Question
from app.brief.extract import (
    FakeBriefProvider,
    GeminiHttpProvider,
    deterministic_fallback_extraction,
    extract_brief,
)
from app.brief.missing_info import find_missing
from app.brief.questions import build_questions
from app.brief.schema import Brief
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests: Extraction Service with Fake Providers
# ---------------------------------------------------------------------------

def test_extract_complete_brief_with_fake_provider():
    """A fake provider returns a full JSON payload conforming to Brief schema."""
    fake_json = json.dumps({
        "design_type": "id_card",
        "event_name": "ACM NIT Surat Hackathon 2026",
        "tagline": "Code the Future",
        "dates": "October 18-19, 2026",
        "venue": "SVNIT Campus, Surat",
        "roles": ["participant", "organizer", "mentor"],
        "counts": {"participant": 200, "mentor": 20, "organizer": 30},
        "fields_to_show": ["name", "role", "id", "team", "photo", "qr"],
        "card_size": "54 x 86 mm",
        "orientation": "portrait",
        "style_hint": "minimal",
        "lanyard_hole": True,
    })
    provider = FakeBriefProvider(response_json=fake_json)
    brief, is_fallback = extract_brief("ID cards for ACM NIT Surat Hackathon", provider=provider)

    assert is_fallback is False
    assert brief.event_name == "ACM NIT Surat Hackathon 2026"
    assert brief.venue == "SVNIT Campus, Surat"
    assert brief.roles == ["participant", "organizer", "mentor"]
    assert brief.counts["participant"] == 200
    assert brief.lanyard_hole is True
    assert len(provider.calls) == 1


def test_extract_partial_brief_preserves_nulls():
    """Missing fields in model output stay None and are not guessed."""
    fake_json = json.dumps({
        "design_type": "id_card",
        "event_name": "TechFest 2026",
        "venue": "Auditorium",
    })
    provider = FakeBriefProvider(response_json=fake_json)
    brief, is_fallback = extract_brief("TechFest at Auditorium", provider=provider)

    assert is_fallback is False
    assert brief.event_name == "TechFest 2026"
    assert brief.venue == "Auditorium"
    assert brief.dates is None
    assert brief.roles is None
    assert brief.counts is None


def test_find_missing_identifies_unspecified_fields():
    """find_missing correctly lists missing required fields."""
    brief = Brief(
        design_type="id_card",
        event_name="SVNIT Code Sprint",
        dates=None,
        venue=None,
        roles=["participant"],
        fields_to_show=None,
    )
    missing = find_missing(brief)
    assert "tagline" in missing
    assert "dates" in missing
    assert "venue" in missing
    assert "fields_to_show" in missing
    assert "event_name" not in missing
    assert "roles" not in missing


def test_build_questions_produces_typed_questions():
    """build_questions constructs Question objects matching schema."""
    missing = ["event_name", "dates", "roles"]
    question_dicts = build_questions(missing)
    questions = [Question.model_validate(q) for q in question_dicts]

    assert len(questions) == 3
    q_map = {q.field: q for q in questions}
    assert q_map["event_name"].skippable is False
    assert q_map["roles"].kind == "multi_choice"
    assert "participant" in q_map["roles"].options


def test_preserves_markdown_wrapped_json_from_provider():
    """Handles markdown code fences ```json ... ``` returned by models."""
    fenced_json = "```json\n{\"design_type\": \"id_card\", \"event_name\": \"Fenced Event\"}\n```"
    provider = FakeBriefProvider(response_json=fenced_json)
    brief, is_fallback = extract_brief("Fenced Event", provider=provider)

    assert is_fallback is False
    assert brief.event_name == "Fenced Event"


def test_provider_malformed_json_triggers_deterministic_fallback():
    """Malformed non-JSON output triggers deterministic fallback safely."""
    provider = FakeBriefProvider(response_json="Sorry, I cannot generate JSON right now.")
    brief, is_fallback = extract_brief("Need cards for mentors and participants", provider=provider)

    assert is_fallback is True
    assert brief.event_name is None  # Never invents event names
    assert "participant" in brief.roles
    assert "mentor" in brief.roles


def test_provider_schema_invalid_output_triggers_fallback():
    """Extra disallowed fields or wrong types trigger fallback without crashing."""
    invalid_schema_json = json.dumps({
        "design_type": "id_card",
        "event_name": "Test",
        "unknown_invented_field": "disallowed by extra='forbid'",
    })
    provider = FakeBriefProvider(response_json=invalid_schema_json)
    brief, is_fallback = extract_brief("Test event", provider=provider)

    assert is_fallback is True


def test_provider_timeout_or_error_triggers_fallback():
    """Provider raising an error triggers deterministic fallback."""
    provider = FakeBriefProvider(error=TimeoutError("Request timed out"))
    brief, is_fallback = extract_brief("Event with participants in portrait", provider=provider)

    assert is_fallback is True
    assert brief.orientation == "portrait"
    assert "participant" in brief.roles


def test_missing_credentials_uses_fallback(monkeypatch):
    """When GEMINI_API_KEY is unset, deterministic fallback is executed without crash."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    brief, is_fallback = extract_brief("Minimal ID card with lanyard hole for mentors")

    assert is_fallback is True
    assert brief.style_hint == "minimal"
    assert brief.lanyard_hole is True
    assert "mentor" in brief.roles


def test_deterministic_fallback_never_hallucinates_details():
    """Fallback extraction extracts explicit keywords only and leaves official info null."""
    brief = deterministic_fallback_extraction("Organizers need landscape badges with minimal techy look")
    assert brief.event_name is None
    assert brief.dates is None
    assert brief.venue is None
    assert brief.roles == ["organizer"]
    assert brief.orientation == "landscape"
    assert brief.style_hint in ("minimal", "techy")


# ---------------------------------------------------------------------------
# API integration tests: POST /brief
# ---------------------------------------------------------------------------

def test_api_brief_default_contract(monkeypatch):
    """POST /brief preserves default mock: true behavior when offline."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    payload = {"text": "Hackathon 2026 at SVNIT Surat with participants and organizers"}
    response = client.post("/brief", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is True
    assert "brief" in data
    assert "missing" in data
    assert "questions" in data
    assert isinstance(data["questions"], list)


def test_api_brief_explicit_mock_parameter():
    """POST /brief?mock=true explicitly preserves mock mode."""
    response = client.post("/brief?mock=true", json={"text": "Any event description"})
    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is True
    assert len(data["questions"]) > 0


def test_api_brief_empty_text_returns_422():
    """POST /brief with empty text fails with 422 Unprocessable Entity."""
    response = client.post("/brief", json={"text": ""})
    assert response.status_code == 422


def test_gemini_http_provider_missing_key_raises_value_error():
    """GeminiHttpProvider raises ValueError when instantiated without an API key."""
    provider = GeminiHttpProvider(api_key="")
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        provider.generate_brief_json("sample text")


# ---------------------------------------------------------------------------
# Unit & integration tests: GeminiGenaiProvider (official SDK)
# ---------------------------------------------------------------------------

def test_gemini_genai_provider_missing_key_raises_value_error(monkeypatch):
    """GeminiGenaiProvider raises ValueError when instantiated without an API key."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from app.brief.extract import GeminiGenaiProvider
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
        GeminiGenaiProvider(api_key="")


def test_gemini_genai_provider_mock_successful_generation(monkeypatch):
    """GeminiGenaiProvider calls google-genai client and returns structured JSON."""
    from unittest.mock import MagicMock
    from app.brief.extract import GeminiGenaiProvider

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "design_type": "id_card",
        "event_name": "ACM Tech Con 2026",
        "dates": "Nov 15-16, 2026",
        "venue": "Convention Center",
        "roles": ["participant", "speaker"],
    })

    provider = GeminiGenaiProvider(api_key="mock-api-key")
    provider._client.models.generate_content = MagicMock(return_value=mock_response)

    result_json = provider.generate_brief_json("ACM Tech Con on Nov 15-16 at Convention Center for participants and speakers")
    assert "ACM Tech Con 2026" in result_json

    brief, is_fallback = extract_brief("any text", provider=provider)
    assert is_fallback is False
    assert brief.event_name == "ACM Tech Con 2026"
    assert brief.dates == "Nov 15-16, 2026"
    assert brief.roles == ["participant", "speaker"]


def test_gemini_genai_provider_auth_error_triggers_fallback():
    """Authentication errors (401/403) in GeminiGenaiProvider trigger deterministic fallback safely."""
    from unittest.mock import MagicMock
    from google.genai import errors
    from app.brief.extract import GeminiGenaiProvider

    provider = GeminiGenaiProvider(api_key="invalid-api-key")
    provider._client.models.generate_content = MagicMock(
        side_effect=errors.APIError(403, {"error": {"message": "API key not valid", "status": "PERMISSION_DENIED"}})
    )

    brief, is_fallback = extract_brief("TechFest organizers in landscape", provider=provider)
    assert is_fallback is True
    assert brief.event_name is None
    assert brief.roles == ["organizer"]
    assert brief.orientation == "landscape"


def test_gemini_genai_provider_quota_rate_limit_triggers_fallback():
    """Rate limit or quota errors (429) trigger deterministic fallback safely."""
    from unittest.mock import MagicMock
    from google.genai import errors
    from app.brief.extract import GeminiGenaiProvider

    provider = GeminiGenaiProvider(api_key="mock-key")
    provider._client.models.generate_content = MagicMock(
        side_effect=errors.APIError(429, {"error": {"message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}})
    )

    brief, is_fallback = extract_brief("Hackathon participants in minimal style", provider=provider)
    assert is_fallback is True
    assert brief.style_hint == "minimal"
    assert "participant" in brief.roles


def test_gemini_genai_provider_timeout_triggers_fallback():
    """Timeout during SDK generation triggers deterministic fallback safely."""
    from unittest.mock import MagicMock
    from app.brief.extract import GeminiGenaiProvider

    provider = GeminiGenaiProvider(api_key="mock-key")
    provider._client.models.generate_content = MagicMock(
        side_effect=TimeoutError("Request timed out after 15 seconds")
    )

    brief, is_fallback = extract_brief("Conference with mentors and lanyard hole", provider=provider)
    assert is_fallback is True
    assert "mentor" in brief.roles
    assert brief.lanyard_hole is True


def test_gemini_genai_provider_empty_response_triggers_fallback():
    """Empty or whitespace response from model triggers fallback safely."""
    from unittest.mock import MagicMock
    from app.brief.extract import GeminiGenaiProvider

    mock_response = MagicMock()
    mock_response.text = "   "

    provider = GeminiGenaiProvider(api_key="mock-key")
    provider._client.models.generate_content = MagicMock(return_value=mock_response)

    brief, is_fallback = extract_brief("Event with judges in portrait", provider=provider)
    assert is_fallback is True
    assert brief.orientation == "portrait"
    assert "judge" in brief.roles


def test_api_brief_endpoint_live_gemini_success_sets_mock_false(monkeypatch):
    """When live Gemini extraction succeeds, POST /brief returns mock: false and populated fields."""
    from unittest.mock import MagicMock
    from app.brief.extract import GeminiGenaiProvider

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "design_type": "id_card",
        "event_name": "NIT Surat Annual Hackathon 2026",
        "tagline": "Innovate Every Day",
        "dates": "December 5-7, 2026",
        "venue": "SVNIT Central Hall",
        "roles": ["participant", "organizer", "mentor"],
        "fields_to_show": ["name", "role", "id", "team", "photo", "qr"],
    })

    # Set mock key and mock the SDK client call
    monkeypatch.setenv("GEMINI_API_KEY", "real-mock-key-for-test")
    monkeypatch.setattr(
        "google.genai.models.Models.generate_content",
        MagicMock(return_value=mock_response),
    )

    response = client.post("/brief", json={"text": "Annual Hackathon at SVNIT Central Hall on Dec 5-7"})
    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is False
    assert data["brief"]["event_name"] == "NIT Surat Annual Hackathon 2026"
    assert data["brief"]["dates"] == "December 5-7, 2026"
    assert data["brief"]["venue"] == "SVNIT Central Hall"
    assert "event_name" not in data["missing"]

