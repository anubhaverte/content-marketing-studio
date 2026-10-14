"""Run automatic QA against every bundled sample card."""

from __future__ import annotations

import sys
import warnings

from qa import run_qa
from qa.report import format_issues
from render import spec_adapter
from render.loaders import load_layout, load_theme
from render.renderer import render_card


CHECK_NAMES = (
    "text_overflow",
    "logo_aspect_ratio",
    "contrast",
    "overlap",
    "empty_fields",
    "data_match",
    "resolution",
)


def report(label: str, passed: bool, detail: str) -> bool:
    """Print one PASS/FAIL line."""
    print(f"{'PASS' if passed else 'FAIL'}: {label} - {detail}")
    return passed


def main() -> int:
    """Verify every QA check against all bundled sample people."""
    spec = spec_adapter.load_design_spec()
    layout = load_layout(spec_adapter.spec_layout(spec))
    theme = load_theme(spec_adapter.spec_theme(spec))
    people = spec_adapter.load_people()
    issues_by_person = []
    for person in people:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            svg = render_card(spec, person)
        issues = run_qa(spec, person, svg, layout, theme)
        issues_by_person.append(issues)
        print(f"\nPerson {spec_adapter.person_id(person) or 'unknown'}:")
        print(format_issues(issues))

    results = []
    for check in CHECK_NAMES:
        failures = [
            issue
            for issues in issues_by_person
            for issue in issues
            if issue.check == check and issue.severity == "error"
        ]
        warning_count = sum(
            1
            for issues in issues_by_person
            for issue in issues
            if issue.check == check and issue.severity == "warning"
        )
        results.append(report(
            f"QA {check.replace('_', ' ')}",
            not failures,
            f"{len(failures)} errors, {warning_count} warnings across {len(people)} people",
        ))
    if all(results):
        print("\nPhase 4 verification complete.")
        return 0
    print("\nPhase 4 verification failed. Fix the reported errors and run again.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
