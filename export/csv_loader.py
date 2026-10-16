"""Load and validate people records from CSV or JSON files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from render import spec_adapter


PeopleProblem = dict[str, int | str]


def load_people(path: str | Path) -> tuple[list[spec_adapter.Person], list[PeopleProblem]]:
    """Load valid person records and return row-numbered validation problems."""
    source = Path(path)
    if source.suffix.lower() == ".json":
        rows = _read_json(source)
    elif source.suffix.lower() == ".csv":
        rows = _read_csv(source)
    else:
        raise ValueError(f"People file must be a .csv or .json file: {source}")
    return _validate_rows(rows, source)


def _read_json(path: Path) -> list[dict[str, Any]]:
    """Read a JSON list while preserving JSON entry order."""
    try:
        with path.open(encoding="utf-8") as source:
            rows = json.load(source)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read people data {path}: {error}") from error
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"People data must be a JSON list of objects: {path}")
    return rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    """Read CSV records with case-insensitive, whitespace-trimmed headers."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise ValueError(f"CSV file has no header row: {path}")
            headers = [header.strip().casefold() for header in reader.fieldnames]
            if len(headers) != len(set(headers)):
                raise ValueError(f"CSV file has duplicate headers after normalization: {path}")
            required = {"id", "name", "role", "photo"}
            missing = required - set(headers)
            if missing:
                raise ValueError(
                    f"CSV file is missing required column(s): {', '.join(sorted(missing))}"
                )
            records = []
            for row_number, raw_row in enumerate(reader, start=2):
                row = {
                    headers[index]: value
                    for index, value in enumerate(raw_row.values())
                    if index < len(headers)
                }
                row["_row_number"] = row_number
                records.append(row)
            return records
    except OSError as error:
        raise ValueError(f"Could not read people data {path}: {error}") from error


def _validate_rows(
    rows: list[dict[str, Any]],
    source: Path,
) -> tuple[list[spec_adapter.Person], list[PeopleProblem]]:
    """Keep valid entries and report missing or repeated identity fields."""
    people: list[spec_adapter.Person] = []
    problems: list[PeopleProblem] = []
    seen_ids: set[str] = set()
    for index, source_row in enumerate(rows, start=1):
        row = dict(source_row)
        row_number = row.pop("_row_number", index)
        if not isinstance(row_number, int):
            row_number = index
        person_id = _clean_value(row.get("id"))
        name = _clean_value(row.get("name"))
        role = _clean_value(row.get("role"))
        photo = _clean_value(row.get("photo"))

        if not person_id:
            problems.append({"row": row_number, "reason": "missing id"})
            continue
        if not name:
            problems.append({"row": row_number, "reason": "missing name"})
            continue
        if role not in spec_adapter.ROLES:
            problems.append({
                "row": row_number,
                "reason": f"unknown role {role!r}; expected one of {', '.join(spec_adapter.ROLES)}",
            })
            continue
        if person_id in seen_ids:
            problems.append({"row": row_number, "reason": f"duplicate id {person_id!r}"})
            continue
        seen_ids.add(person_id)
        people.append(spec_adapter.Person(
            {"id": person_id, "name": name, "role": role, "photo": photo},
            str(source.resolve()),
        ))
    return people, problems


def _clean_value(value: Any) -> str | None:
    """Trim string fields and treat empty or non-string values as absent."""
    return value.strip() if isinstance(value, str) and value.strip() else None
