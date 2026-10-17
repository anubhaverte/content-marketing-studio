"""Natural-language refinement: Convert plain-English requests into safe DesignSpec patch operations.

Follows Track 4 non-negotiables:
- AI only suggests visual style hints and spec patches.
- AI NEVER writes names/dates/official details or places text.
- Participant facts (name, id, email, team, role) and event facts are strictly protected.
- Both institutional logos (ACM NIT Surat, SVNIT) must remain intact.
- Deterministic heuristic fallbacks guaranteed when AI is unavailable or fails.
- All operations are strictly validated against an explicit allowlist.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from app.refine.patch import apply_patch

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Explicit allowlist of patchable paths and properties
ALLOWED_PREFIXES = (
    "theme.colors.",
    "theme.role_colors.",
    "theme.fonts.",
    "theme_name",
    "layout_name",
    "elements.",
)

FORBIDDEN_PATHS = {
    "schema_version",
    "event",
    "event.event_name",
    "event.dates",
    "event.venue",
    "page",
    "brand.logos.acm_nitsurat",
    "brand.logos.svnit",
}

FORBIDDEN_SUBSTRINGS = (
    "person",
    "attendee",
    "participant_name",
    "email",
    "logo_acm",
    "logo_svnit",
)


def validate_patch_op(op: dict[str, Any]) -> bool:
    """Validate that a patch operation strictly modifies allowed aesthetic/layout properties."""
    path = op.get("path", "").strip()
    if not path:
        return False

    if path in FORBIDDEN_PATHS or any(path.startswith(f"{fp}.") for fp in FORBIDDEN_PATHS):
        return False

    # Block any attempt to alter identity or logo bindings
    for forbidden in FORBIDDEN_SUBSTRINGS:
        if forbidden in path.lower():
            # Only allow setting properties on elements if not removing/altering the logo asset itself
            if "logo" in forbidden and op.get("op") == "remove":
                return False
            if forbidden != "logo_acm" and forbidden != "logo_svnit":
                return False

    # Must start with an allowed prefix
    if not any(path == prefix.rstrip(".") or path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return False

    # Validate op action
    if op.get("op") not in ("add", "remove", "set"):
        return False

    return True


def _deterministic_nlp_refine(request_text: str, spec: Any) -> list[dict[str, Any]]:
    """Rule-based heuristic refinement turning natural language into patch ops."""
    text = request_text.lower()
    ops: list[dict[str, Any]] = []

    # 1. Photo Shape Refinement
    if "circle" in text or "round photo" in text or "circular" in text:
        ops.append({"op": "set", "path": "elements.photo.shape", "value": "circle"})
    elif "rounded" in text or "square" in text or "rectangle" in text:
        ops.append({"op": "set", "path": "elements.photo.shape", "value": "rounded"})
        if "radius" in text:
            ops.append({"op": "set", "path": "elements.photo.radius", "value": 4})

    # 2. Name Prominence & Typography
    if "prominen" in text or "bigger name" in text or "larger name" in text or "increase name" in text:
        ops.append({"op": "set", "path": "elements.name.max_font", "value": 16})
        ops.append({"op": "set", "path": "elements.name.bold", "value": True})
    elif "smaller name" in text:
        ops.append({"op": "set", "path": "elements.name.max_font", "value": 12})

    if "center name" in text or "centered name" in text:
        ops.append({"op": "set", "path": "elements.name.align", "value": "center"})
    elif "left align name" in text or "left-aligned name" in text:
        ops.append({"op": "set", "path": "elements.name.align", "value": "left"})

    # 3. Theme & Color Styling
    if "dark tech" in text or "dark theme" in text or "dark blue" in text or "dark mode" in text:
        ops.append({"op": "set", "path": "theme_name", "value": "dark_tech"})
        ops.append({"op": "set", "path": "theme.colors.background", "value": "#0B1220"})
        ops.append({"op": "set", "path": "theme.colors.primary", "value": "#1E293B"})
        ops.append({"op": "set", "path": "theme.colors.secondary", "value": "#312E81"})
        ops.append({"op": "set", "path": "theme.colors.accent", "value": "#38BDF8"})
        ops.append({"op": "set", "path": "theme.colors.text", "value": "#F8FAFC"})
    elif "clean light" in text or "light theme" in text or "light mode" in text:
        ops.append({"op": "set", "path": "theme_name", "value": "clean_light"})
        ops.append({"op": "set", "path": "theme.colors.background", "value": "#FFFFFF"})
        ops.append({"op": "set", "path": "theme.colors.primary", "value": "#1F6FEB"})
        ops.append({"op": "set", "path": "theme.colors.secondary", "value": "#EAF1FD"})
        ops.append({"op": "set", "path": "theme.colors.accent", "value": "#38BDF8"})
        ops.append({"op": "set", "path": "theme.colors.text", "value": "#0B1220"})
    elif "bold event" in text or "bold theme" in text:
        ops.append({"op": "set", "path": "theme_name", "value": "bold_event"})
        ops.append({"op": "set", "path": "theme.colors.background", "value": "#FFF7ED"})
        ops.append({"op": "set", "path": "theme.colors.accent", "value": "#E11D48"})

    # 4. Formal / Professional Tone (e.g. Coordinator / Organizer)
    if "formal" in text or "coordinator" in text or "organizer" in text:
        ops.append({"op": "set", "path": "theme.role_colors.organizer", "value": "#D9480F"})
        ops.append({"op": "set", "path": "elements.name.bold", "value": True})

    # 5. Font Refinement
    if "poppins" in text:
        ops.append({"op": "set", "path": "theme.fonts.heading", "value": "Poppins"})
    elif "inter" in text:
        ops.append({"op": "set", "path": "theme.fonts.heading", "value": "Inter"})
    elif "space grotesk" in text:
        ops.append({"op": "set", "path": "theme.fonts.heading", "value": "Space Grotesk"})

    # 6. Direct hex color override if detected
    hex_match = re.search(r"#(?:[0-9a-fA-F]{3}){1,2}\b", request_text)
    if hex_match:
        color = hex_match.group(0).upper()
        if "background" in text:
            ops.append({"op": "set", "path": "theme.colors.background", "value": color})
        elif "primary" in text:
            ops.append({"op": "set", "path": "theme.colors.primary", "value": color})
        elif "accent" in text:
            ops.append({"op": "set", "path": "theme.colors.accent", "value": color})

    return ops


DESIGN_KEYWORDS = (
    "color", "theme", "photo", "name", "font", "size", "dark", "light", "bold",
    "align", "center", "circle", "round", "square", "border", "accent", "primary",
    "background", "margin", "padding", "badge", "role", "heading", "text", "layout",
    "minimal", "split", "classic", "poppins", "inter", "banner", "line", "qr", "logo",
    "bigger", "smaller", "larger", "prominent", "increase", "decrease", "mode", "style", "palette"
)


def has_design_intent(request_text: str) -> bool:
    """Check if the prompt contains words or patterns relating to visual design adjustments."""
    if not request_text or not request_text.strip():
        return False
    if re.search(r"#(?:[0-9a-fA-F]{3}){1,2}\b", request_text):
        return True
    text = request_text.lower()
    return any(kw in text for kw in DESIGN_KEYWORDS)


def _call_gemini_refine(request_text: str, spec: Any) -> list[dict[str, Any]] | None:
    """Optionally query Gemini API for a structured patch if GEMINI_API_KEY is configured."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    if not has_design_intent(request_text):
        return []

    import httpx

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_MODEL}:generateContent?key={api_key}"
    system_prompt = (
        "You are an ID Card Design Spec refinement engine. "
        "Convert the user's natural language request into a minimal list of JSON patch operations to modify the DesignSpec. "
        "Allowed paths: theme.colors.<color>, theme.role_colors.<role>, theme.fonts.<family>, "
        "elements.<id>.<property> (e.g. elements.photo.shape, elements.name.max_font, elements.name.align). "
        "NEVER modify event details, participant data, or delete institutional logos. "
        "If the user request contains no styling or design instructions, return an empty array []. "
        "Return a valid JSON array of objects with keys 'op' (set/add/remove), 'path' (string), and 'value'."
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"User Request: {request_text}\nCurrent Layout: {getattr(spec, 'layout_name', 'classic')}, Theme: {getattr(spec, 'theme_name', 'clean_light')}"}
                ],
            }
        ],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        },
    }

    try:
        resp = httpx.post(url, json=payload, timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                return parsed
    except Exception as exc:
        logger.warning("Gemini refinement API error: %s; using deterministic fallback", exc)

    return None


def nl_to_patch(request_text: str, spec: Any) -> list[dict[str, Any]]:
    """Convert natural-language instructions into validated DesignSpec patch operations.

    Args:
        request_text: Plain-English refinement prompt from organizer.
        spec: The active DesignSpec instance.

    Returns:
        List of verified patch operations conforming to the explicit allowlist.
    """
    if not has_design_intent(request_text):
        return []

    raw_ops = _call_gemini_refine(request_text, spec)
    if raw_ops is None:
        raw_ops = _deterministic_nlp_refine(request_text, spec)

    # Strictly filter and validate all operations against allowlist
    validated_ops = [op for op in raw_ops if validate_patch_op(op)]
    return validated_ops
