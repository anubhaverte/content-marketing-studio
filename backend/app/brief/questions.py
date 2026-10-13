"""Turn missing Brief fields into short follow-up questions for the organizer."""
from typing import Any

QUESTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "event_name": {
        "text": "What is the official name of the event?",
        "kind": "text",
        "options": None,
        "default": None,
        "skippable": False,
    },
    "tagline": {
        "text": "What is the tagline or subtitle for the event?",
        "kind": "text",
        "options": None,
        "default": None,
        "skippable": True,
    },
    "dates": {
        "text": "When will the event take place (e.g., Oct 10-12, 2026)?",
        "kind": "text",
        "options": None,
        "default": None,
        "skippable": True,
    },
    "venue": {
        "text": "Where is the event venue located?",
        "kind": "text",
        "options": None,
        "default": None,
        "skippable": True,
    },
    "roles": {
        "text": "Which participant roles should receive badges?",
        "kind": "multi_choice",
        "options": ["participant", "organizer", "mentor"],
        "default": ["participant", "organizer", "mentor"],
        "skippable": True,
    },
    "fields_to_show": {
        "text": "Which person details should be printed on the card?",
        "kind": "multi_choice",
        "options": ["name", "role", "id", "team", "photo", "qr"],
        "default": ["name", "role", "id", "team", "photo", "qr"],
        "skippable": True,
    },
    "card_size": {
        "text": "What is the preferred card size?",
        "kind": "choice",
        "options": ["54 x 86 mm (CR80 Standard)", "A6 Event Badge"],
        "default": "54 x 86 mm (CR80 Standard)",
        "skippable": True,
    },
    "orientation": {
        "text": "Should the card be portrait or landscape?",
        "kind": "choice",
        "options": ["portrait", "landscape"],
        "default": "portrait",
        "skippable": True,
    },
    "style_hint": {
        "text": "What visual style do you prefer (e.g. minimal, techy, elegant)?",
        "kind": "text",
        "options": None,
        "default": "minimal",
        "skippable": True,
    },
    "lanyard_hole": {
        "text": "Does the card require a punched lanyard hole slot?",
        "kind": "boolean",
        "options": None,
        "default": False,
        "skippable": True,
    },
}


def build_questions(missing: list[str]) -> list[dict[str, Any]]:
    """Return one question dict per missing field, matching Question schema attributes."""
    questions: list[dict[str, Any]] = []
    for field_name in missing:
        defn = QUESTION_DEFINITIONS.get(field_name)
        if defn:
            questions.append(
                {
                    "field": field_name,
                    "text": defn["text"],
                    "kind": defn["kind"],
                    "options": defn.get("options"),
                    "default": defn.get("default"),
                    "skippable": defn.get("skippable", True),
                }
            )
        else:
            questions.append(
                {
                    "field": field_name,
                    "text": f"Please provide a value for {field_name.replace('_', ' ')}:",
                    "kind": "text",
                    "options": None,
                    "default": None,
                    "skippable": True,
                }
            )
    return questions
