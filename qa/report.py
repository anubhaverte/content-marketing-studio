"""Format QA issues for people and API consumers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from qa.checks import Issue


def format_issues(issues: Iterable[Issue]) -> str:
    """Return a readable multi-line summary of card QA issues."""
    rows = [
        f"{issue.severity.upper()}: {issue.check} (person {issue.person_id or 'unknown'}) - {issue.message}"
        for issue in issues
    ]
    return "\n".join(rows) if rows else "No QA issues."


def issues_to_dict(issues: Iterable[Issue]) -> list[dict[str, str | None]]:
    """Convert QA issues to JSON-friendly dictionaries."""
    return [asdict(issue) for issue in issues]
