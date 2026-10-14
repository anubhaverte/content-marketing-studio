"""Stable application-facing entry points for card rendering and export jobs."""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from export.batch import export_batch
from export.csv_loader import load_people
from export.exporters import export_card
from export.print_sheet import export_print_sheet
from export.settings import ExportSettings, PrintSheetSettings
from qa import run_qa
from qa.report import issues_to_dict
from render import spec_adapter
from render.loaders import LAYOUTS_DIR, THEMES_DIR, load_layout, load_theme
from render.renderer import render_card, render_preview


SpecInput = spec_adapter.DesignSpec | Mapping[str, Any]
PersonInput = spec_adapter.Person | Mapping[str, Any]


def render_card_svg(spec: SpecInput, person: PersonInput) -> str:
    """Render one person's card as SVG.

    Inputs are a normalized DesignSpec/Person or decoded JSON objects. Returns
    SVG text. Raises ValueError for invalid spec/person/template values and
    RuntimeError or OSError for renderer/native-library failures.
    """
    normalized_spec = spec_adapter.normalize_design_spec(spec)
    normalized_person = spec_adapter.normalize_person(person)
    return render_card(normalized_spec, normalized_person)


def render_preview_svg(spec: SpecInput, role: str) -> str:
    """Render the bundled sample person's card for a role as SVG.

    Input is a normalized DesignSpec or decoded JSON object and one supported
    role. Returns SVG text. Raises ValueError for invalid specs, roles, or
    missing sample people, and RuntimeError or OSError for renderer failures.
    """
    return render_preview(spec_adapter.normalize_design_spec(spec), role)


def run_qa_for_card(spec: SpecInput, person: PersonInput) -> list[dict[str, str | None]]:
    """Run the existing QA checks and return JSON-friendly issue dictionaries.

    Inputs are a normalized DesignSpec/Person or decoded JSON objects. Returns
    dictionaries with check, severity, person_id, and message keys. Raises
    ValueError for invalid spec/person/template data; check-level failures are
    returned as error issues by qa.run_qa.
    """
    normalized_spec = spec_adapter.normalize_design_spec(spec)
    normalized_person = spec_adapter.normalize_person(person)
    svg = render_card(normalized_spec, normalized_person)
    layout = load_layout(spec_adapter.spec_layout(normalized_spec))
    theme = load_theme(spec_adapter.spec_theme(normalized_spec))
    return issues_to_dict(run_qa(normalized_spec, normalized_person, svg, layout, theme))


def export_card_bytes(
    spec: SpecInput,
    person: PersonInput,
    settings_dict: Mapping[str, Any],
) -> bytes:
    """Export one card to SVG, PDF, or PNG bytes.

    Inputs are a normalized DesignSpec/Person or decoded JSON objects plus an
    ExportSettings dictionary. Returns the selected format's bytes. Raises
    ValueError for invalid settings or card data and RuntimeError/OSError when
    the selected exporter cannot run.
    """
    settings = ExportSettings.from_dict(settings_dict)
    return export_card(
        spec_adapter.normalize_design_spec(spec),
        spec_adapter.normalize_person(person),
        settings,
    )


def export_batch_zip(
    spec: SpecInput,
    people: Sequence[PersonInput],
    settings_dict: Mapping[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    """Export people to the existing batch ZIP and return its report separately.

    Inputs are a normalized DesignSpec/people or decoded JSON objects and an
    ExportSettings dictionary. Returns (ZIP bytes, report dictionary). Raises
    ValueError for invalid settings/spec data and OSError for ZIP output
    failures. Per-person rendering/export failures are recorded in the report.
    """
    normalized_spec = spec_adapter.normalize_design_spec(spec)
    normalized_people = [spec_adapter.normalize_person(person) for person in people]
    archive_bytes = export_batch(
        normalized_spec,
        normalized_people,
        ExportSettings.from_dict(settings_dict),
    )
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        report = json.loads(archive.read("report.json"))
    return archive_bytes, report


def export_print_sheet_pdf(
    spec: SpecInput,
    people: Sequence[PersonInput],
    paper: str,
    settings_dict: Mapping[str, Any],
) -> tuple[bytes, dict[str, Any]]:
    """Export a printable sheet as PDF bytes and a batch-style report.

    Inputs are a normalized DesignSpec/people or decoded JSON objects, paper
    "A4" or "A3", and a PrintSheetSettings dictionary. Returns (PDF bytes,
    report dictionary). Raises ValueError for invalid paper/settings/spec/card
    data and RuntimeError/OSError for renderer or native-library failures.
    """
    normalized_spec = spec_adapter.normalize_design_spec(spec)
    normalized_people = [spec_adapter.normalize_person(person) for person in people]
    report: dict[str, Any] = {}
    pdf_bytes = export_print_sheet(
        normalized_spec,
        normalized_people,
        paper,
        PrintSheetSettings.from_dict(settings_dict),
        report=report,
    )
    return pdf_bytes, report


def load_people_file(path: str | Path) -> tuple[list[spec_adapter.Person], list[dict[str, int | str]]]:
    """Load validated people and row-level problems from a CSV or JSON file.

    Input is a path to the people file. Returns normalized Person objects and
    JSON-friendly problem dictionaries. Raises ValueError for unsupported file
    formats, unreadable files, or invalid top-level JSON/CSV structure.
    """
    return load_people(path)


def list_layouts() -> list[str]:
    """Return sorted layout filename stems found in templates/layouts."""
    return sorted(path.stem for path in LAYOUTS_DIR.glob("*.json"))


def list_themes() -> list[str]:
    """Return sorted theme filename stems found in templates/themes."""
    return sorted(path.stem for path in THEMES_DIR.glob("*.json"))


__all__ = [
    "render_card_svg",
    "render_preview_svg",
    "run_qa_for_card",
    "export_card_bytes",
    "export_batch_zip",
    "export_print_sheet_pdf",
    "load_people_file",
    "list_layouts",
    "list_themes",
]
