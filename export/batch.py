"""Export collections of cards into ZIP archives or a combined PDF."""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Sequence

from pypdf import PdfReader, PdfWriter

from export.exporters import export_card
from export.settings import ExportSettings
from qa import run_qa
from qa.report import issues_to_dict
from render import spec_adapter
from render.loaders import load_layout, load_theme


def export_batch(
    spec: spec_adapter.DesignSpec,
    people: Sequence[spec_adapter.Person],
    settings: ExportSettings,
    out_path: str | Path | None = None,
    *,
    skipped_rows: Sequence[dict[str, int | str]] = (),
    layout: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
) -> bytes:
    """Export each person independently and package results plus a JSON report."""
    if layout is None:
        layout = load_layout(spec_adapter.spec_layout(spec))
    if theme is None:
        theme = load_theme(spec_adapter.spec_theme(spec))
    extension = settings.format
    records: list[dict[str, object]] = []
    payloads: list[tuple[str, bytes]] = []
    used_names: set[str] = set()
    qa_issue_count = 0

    for person in people:
        person_id = _person_id(person)
        issue_dicts: list[dict[str, str | None]] = []
        try:
            svg = _render_for_qa(spec, person, layout=layout, theme=theme)
            issues = run_qa(spec, person, svg, layout, theme)
            issue_dicts = issues_to_dict(issues)
            qa_issue_count += len(issue_dicts)
            exported = export_card(spec, person, settings, layout=layout, theme=theme)
            role = spec_adapter.person_role(person)
            filename = _filename(person_id, role, extension, used_names)
            payloads.append((filename, exported))
            records.append({
                "id": person_id,
                "role": role,
                "status": "exported",
                "file": filename,
                "qa_issues": issue_dicts,
            })
        except Exception as error:
            records.append({
                "id": person_id,
                "status": "failed",
                "reason": str(error),
                "qa_issues": issue_dicts,
            })

    exported_count = len(payloads)
    failed_count = len(people) - exported_count
    report = {
        "totals": {
            "people": len(people),
            "exported": exported_count,
            "failed": failed_count,
            "skipped_rows": len(skipped_rows),
            "qa_issues": qa_issue_count,
        },
        "people": records,
        "skipped_rows": list(skipped_rows),
        "settings": settings.to_dict(),
    }
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for filename, data in payloads:
            output.writestr(filename, data)
        output.writestr(
            "report.json",
            json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    archive_bytes = archive.getvalue()
    if out_path is not None:
        destination = Path(out_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive_bytes)
    return archive_bytes


def export_batch_pdf(
    spec: spec_adapter.DesignSpec,
    people: Sequence[spec_adapter.Person],
    settings: ExportSettings,
    *,
    layout: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
) -> bytes:
    """Return one vector PDF page per person in the input sequence."""
    writer = PdfWriter()
    for person in people:
        person_id = _person_id(person) or "unknown"
        try:
            card_pdf = export_card(
                spec,
                person,
                ExportSettings(
                    format="pdf",
                    dpi=settings.dpi,
                    orientation=settings.orientation,
                    bleed=settings.bleed,
                ),
                layout=layout,
                theme=theme,
            )
            writer.append(PdfReader(io.BytesIO(card_pdf)))
        except Exception as error:
            raise ValueError(f"Could not export PDF for person {person_id!r}: {error}") from error
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _render_for_qa(
    spec: spec_adapter.DesignSpec,
    person: spec_adapter.Person,
    *,
    layout: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
) -> str:
    """Render a card once for QA before its output export."""
    if layout is not None and theme is not None:
        from render.renderer import _render
        return _render(spec, person, layout, theme)
    from render.renderer import render_card

    return render_card(spec, person)


def _person_id(person: spec_adapter.Person) -> str | None:
    """Read an ID for reporting without preventing failure reporting."""
    try:
        return spec_adapter.person_id(person)
    except (TypeError, ValueError):
        return None


def _filename(
    person_id: str | None,
    role: str,
    extension: str,
    used_names: set[str],
) -> str:
    """Create a Windows-safe, collision-resistant ID-based archive filename."""
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", person_id or "").strip(" .-_")
    if not safe_id:
        safe_id = "person"
    if safe_id.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }:
        safe_id = f"_{safe_id}"
    safe_role = re.sub(r"[^A-Za-z0-9_-]+", "-", role).strip("-") or "unknown"
    base = f"{safe_id}-{safe_role}"
    name = f"{base}.{extension}"
    suffix = 2
    while name.casefold() in used_names:
        name = f"{base}-{suffix}.{extension}"
        suffix += 1
    used_names.add(name.casefold())
    return name
