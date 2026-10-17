"""Extract structured event Brief from plain-English requests using Gemini or clean fallbacks.

Follows Track 4 non-negotiables:
- AI only extracts explicitly provided parameters.
- AI never invents event names, dates, venues, or attendee details.
- Unknown fields stay null.
- Deterministic fallback when AI is unavailable or fails.
- Pydantic schema validation is strictly enforced.
"""
import json
import os
import re
from typing import Any, Optional, Protocol

import httpx
from pydantic import ValidationError

import logging

from app.brief.schema import Brief

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_INSTRUCTION = """You are a strict data extraction assistant for event ID card design.
Extract ONLY event parameters that are explicitly mentioned in the user's text.
Do NOT guess, assume, or invent details. If the user does not state a detail, leave it null.
Return a valid JSON object matching the requested schema with keys:
- design_type: string (default "id_card")
- event_name: string or null
- tagline: string or null
- dates: string or null
- venue: string or null
- roles: array of strings or null (e.g. ["participant", "organizer", "mentor"])
- counts: object mapping role to integer count or null (e.g. {"participant": 200})
- fields_to_show: array of strings or null (e.g. ["name", "role", "id", "team", "photo", "qr"])
- card_size: string or null
- orientation: string or null ("portrait" or "landscape")
- style_hint: string or null (e.g. "minimal", "techy")
- lanyard_hole: boolean or null
"""


def _clean_schema_for_gemini(schema: Any) -> Any:
    """Remove OpenAPI properties unsupported by the Gemini API (e.g. additionalProperties)."""
    if isinstance(schema, dict):
        return {
            k: _clean_schema_for_gemini(v)
            for k, v in schema.items()
            if k not in ("additionalProperties",)
        }
    elif isinstance(schema, list):
        return [_clean_schema_for_gemini(item) for item in schema]
    return schema


class BriefProvider(Protocol):
    """Protocol for brief extraction AI providers."""

    def generate_brief_json(self, user_text: str) -> str:
        """Return raw JSON string extracted from user text."""
        ...


class FakeBriefProvider:
    """Test fake provider returning predetermined JSON responses or raising simulated errors."""

    def __init__(self, response_json: Optional[str] = None, error: Optional[Exception] = None):
        self.response_json = response_json or "{}"
        self.error = error
        self.calls: list[str] = []

    def generate_brief_json(self, user_text: str) -> str:
        self.calls.append(user_text)
        if self.error:
            raise self.error
        return self.response_json


class GeminiGenaiProvider:
    """Official Google GenAI SDK provider for structured brief extraction."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model = (model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)).strip()
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        from google import genai
        self._client = genai.Client(api_key=self.api_key)

    def generate_brief_json(self, user_text: str) -> str:
        """Call Gemini via google-genai SDK with structured output enforcement."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=_clean_schema_for_gemini(Brief.model_json_schema()),
            temperature=0.0,
        )

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user_text,
                config=config,
            )
        except errors.APIError as e:
            code = getattr(e, "code", None)
            err_msg = str(e)
            if code in (401, 403) or "API_KEY_INVALID" in err_msg or "PERMISSION_DENIED" in err_msg:
                raise PermissionError(f"Gemini API authentication failed (code {code}): invalid API key") from e
            if code == 429 or "RESOURCE_EXHAUSTED" in err_msg:
                raise RuntimeError("Gemini API rate limit or quota exceeded (429)") from e
            raise RuntimeError(f"Gemini API error ({code}): {getattr(e, 'message', str(e))}") from e
        except Exception as e:
            err_lower = str(e).lower()
            if "timeout" in err_lower or "timed out" in err_lower:
                raise TimeoutError(f"Gemini API request timed out: {e}") from e
            raise RuntimeError(f"Gemini request failed: {e}") from e

        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise ValueError("Empty response received from Gemini model")
        return text.strip()


class GeminiHttpProvider:
    """Provider communicating with the Gemini REST API using httpx."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 10.0,
    ):
        if api_key is not None:
            self.api_key = api_key.strip()
        else:
            self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def generate_brief_json(self, user_text: str) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        url = GEMINI_API_URL_TEMPLATE.format(model=self.model)
        params = {"key": self.api_key}

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_INSTRUCTION}\n\nUser request:\n{user_text}"}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, params=params, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Gemini API request timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Gemini API returned HTTP {e.response.status_code}: {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Gemini network error: {e}") from e

        # Extract text from candidate
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned by Gemini")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("No content parts in Gemini candidate")
            text_content = parts[0].get("text", "")
            return text_content
        except (KeyError, IndexError) as e:
            raise ValueError(f"Malformed Gemini response structure: {e}") from e


def deterministic_fallback_extraction(user_text: str) -> Brief:
    """Heuristic, deterministic fallback extraction when AI is disabled or fails.

    Extracts explicitly mentioned keywords without hallucinating values.
    """
    text_lower = user_text.lower()

    # Detect known roles
    detected_roles = []
    for r in ["participant", "organizer", "mentor", "volunteer", "speaker", "judge"]:
        if re.search(rf"\b{r}s?\b", text_lower):
            detected_roles.append(r)
    roles = detected_roles if detected_roles else None

    # Detect orientation
    orientation = None
    if "landscape" in text_lower:
        orientation = "landscape"
    elif "portrait" in text_lower:
        orientation = "portrait"

    # Detect style hint
    style_hint = None
    for hint in [
        "dark tech", "dark_tech", "dark", "techy", "tech", "cyber",
        "bold event", "bold_event", "bold", "vibrant",
        "clean light", "clean_light", "clean", "minimal",
        "split", "sidebar", "two-tone",
        "classic", "formal", "modern", "gradient",
    ]:
        if hint in text_lower:
            style_hint = hint.replace(" ", "_")
            break

    # Detect lanyard
    lanyard_hole = None
    if "lanyard" in text_lower or "hole" in text_lower or "punch" in text_lower:
        lanyard_hole = True

    return Brief(
        design_type="id_card",
        event_name=None,  # AI never invents event names
        tagline=None,
        dates=None,
        venue=None,
        roles=roles,
        counts=None,
        fields_to_show=None,
        card_size=None,
        orientation=orientation,
        style_hint=style_hint,
        lanyard_hole=lanyard_hole,
    )


def extract_brief(
    user_text: str,
    provider: Optional[BriefProvider] = None,
) -> tuple[Brief, bool]:
    """Extract a validated Brief from user text.

    Args:
        user_text: Plain-English brief description from the user.
        provider: AI provider implementation. If None and GEMINI_API_KEY is set,
                  GeminiGenaiProvider (official google-genai SDK) is used.
                  If GEMINI_API_KEY is not set or call fails, deterministic fallback
                  is returned and mock=True is preserved.

    Returns:
        tuple (brief: Brief, is_mock_or_fallback: bool)
    """
    if not user_text or not user_text.strip():
        return Brief(design_type="id_card"), True

    # If provider is not passed and no GEMINI_API_KEY is configured, use deterministic fallback
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    active_provider = provider
    if active_provider is None:
        if not api_key:
            logger.info("GEMINI_API_KEY is not configured; using deterministic offline fallback.")
            return deterministic_fallback_extraction(user_text), True
        try:
            active_provider = GeminiGenaiProvider(api_key=api_key)
        except Exception as init_err:
            logger.warning("Failed to initialize GeminiGenaiProvider: %s. Falling back to HTTP provider.", init_err)
            active_provider = GeminiHttpProvider(api_key=api_key)

    # Attempt AI extraction with strict JSON parsing and Pydantic validation
    try:
        raw_json = active_provider.generate_brief_json(user_text)

        # Clean potential markdown fences ```json ... ```
        cleaned_json = raw_json.strip()
        if cleaned_json.startswith("```"):
            cleaned_json = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_json)
            cleaned_json = re.sub(r"\n?```$", "", cleaned_json).strip()

        data = json.loads(cleaned_json)
        if not isinstance(data, dict):
            raise ValueError("Provider output must be a JSON object")

        # Validate with strict Brief schema (forbids unknown fields)
        brief = Brief.model_validate(data)
        return brief, False

    except PermissionError as e:
        logger.warning("Gemini authentication failure: %s. Triggering offline fallback.", e)
        return deterministic_fallback_extraction(user_text), True
    except TimeoutError as e:
        logger.warning("Gemini API request timed out: %s. Triggering offline fallback.", e)
        return deterministic_fallback_extraction(user_text), True
    except ValidationError as e:
        logger.warning("Gemini model output failed Pydantic schema validation: %s. Triggering offline fallback.", e)
        return deterministic_fallback_extraction(user_text), True
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Gemini model output malformed JSON: %s. Triggering offline fallback.", e)
        return deterministic_fallback_extraction(user_text), True
    except RuntimeError as e:
        logger.warning("Gemini runtime error: %s. Triggering offline fallback.", e)
        return deterministic_fallback_extraction(user_text), True
    except Exception as e:
        logger.warning("Gemini extraction failed (%s: %s). Triggering offline fallback.", type(e).__name__, e)
        return deterministic_fallback_extraction(user_text), True
