"""Check participant data and report problems. Never fixes names silently.

Validates participant data against the Person schema, tracks duplicate IDs,
unknown roles, and formats issue tallies.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.data.csv_loader import RowError
from app.spec.constants import DEFAULT_ROLES
from app.spec.schema import Person


@dataclass
class ValidationSummary:
    """Detailed summary of attendee data validation."""
    valid_people: list[Person] = field(default_factory=list)
    invalid_rows: list[RowError] = field(default_factory=list)
    issues: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def validate_people(
    rows: list[dict[str, Any]],
    allowed_roles: Optional[set[str]] = None,
) -> ValidationSummary:
    """Flag missing names, unknown roles, duplicate IDs, very long names, and missing details.

    Never fixes names or attendee details silently: problematic rows are reported
    with their 1-indexed row number, field name, and specific error message.

    Args:
        rows: List of dictionary records, typically produced by csv_loader.
              Each row may contain '_row_num'.
        allowed_roles: Set of valid role strings. Defaults to DEFAULT_ROLES
                       ("participant", "organizer", "mentor").

    Returns:
        ValidationSummary containing valid Person models, invalid rows, and issues summary.
    """
    valid_roles = allowed_roles if allowed_roles is not None else set(DEFAULT_ROLES)

    valid_people: list[Person] = []
    invalid_rows: list[RowError] = []
    warnings: list[str] = []

    # Issue tallies aligning with expected validation metrics
    issues: dict[str, int] = {
        "missing_names": 0,
        "unknown_roles": 0,
        "duplicate_ids": 0,
        "missing_photo": 0,
        "missing_team": 0,
        "missing_id": 0,
        "very_long_names": 0,
        "single_word_names": 0,
        "very_short_names": 0,
        "accented_names": 0,
        "messy_whitespace_or_case": 0,
    }

    seen_ids: dict[str, int] = {}  # id -> first row number seen

    for idx, row in enumerate(rows, start=2):  # default to row 2 assuming header at row 1
        row_num = row.get("_row_num", idx)

        # 1. Name validation
        raw_name = row.get("name")
        name_str = str(raw_name) if raw_name is not None else ""
        stripped_name = name_str.strip()

        if not stripped_name:
            issues["missing_names"] += 1
            invalid_rows.append(
                RowError(
                    row_number=row_num,
                    field="name",
                    message="Missing or empty attendee name",
                    raw_data=row,
                )
            )
            continue

        # Inspect name characteristics without modifying it silently
        if len(stripped_name) >= 40:
            issues["very_long_names"] += 1
        if len(stripped_name) <= 3:
            issues["very_short_names"] += 1
        if " " not in stripped_name and len(stripped_name) >= 4:
            issues["single_word_names"] += 1
        if any(ord(c) > 127 for c in name_str):
            issues["accented_names"] += 1
        if name_str != stripped_name or name_str.isupper() or name_str.islower():
            issues["messy_whitespace_or_case"] += 1

        # 2. Role validation
        raw_role = row.get("role")
        role_str = str(raw_role).strip() if raw_role is not None else "participant"
        if not role_str:
            role_str = "participant"

        if role_str.lower() not in valid_roles:
            issues["unknown_roles"] += 1
            warnings.append(
                f"Row {row_num}: Unknown role '{role_str}'. Expected one of {sorted(valid_roles)}."
            )

        # 3. ID and Duplicate ID validation
        raw_id = row.get("id")
        id_str = str(raw_id).strip() if raw_id is not None and str(raw_id).strip() else None

        if not id_str:
            issues["missing_id"] += 1
        else:
            if id_str in seen_ids:
                issues["duplicate_ids"] += 1
                warnings.append(
                    f"Row {row_num}: Duplicate ID '{id_str}' already used at row {seen_ids[id_str]}."
                )
            else:
                seen_ids[id_str] = row_num

        # 4. Optional fields
        raw_team = row.get("team")
        team_str = str(raw_team).strip() if raw_team is not None and str(raw_team).strip() else None
        if not team_str:
            issues["missing_team"] += 1

        raw_photo = row.get("photo")
        photo_str = str(raw_photo).strip() if raw_photo is not None and str(raw_photo).strip() else None
        if not photo_str:
            issues["missing_photo"] += 1

        raw_email = row.get("email")
        email_str = str(raw_email).strip() if raw_email is not None and str(raw_email).strip() else None

        raw_qr = row.get("qr_url")
        qr_str = str(raw_qr).strip() if raw_qr is not None and str(raw_qr).strip() else None

        # Collect extra fields
        known_keys = {"_row_num", "name", "role", "id", "team", "email", "photo", "qr_url"}
        extra_fields = {
            k: str(v) for k, v in row.items()
            if k not in known_keys and v is not None and str(v).strip()
        }

        # Build Person model (keeping name as provided, without silently inventing/reformatting)
        try:
            person = Person(
                name=stripped_name,
                role=role_str.lower() if role_str.lower() in valid_roles else role_str,
                id=id_str,
                team=team_str,
                email=email_str,
                photo=photo_str,
                qr_url=qr_str,
                extra=extra_fields,
            )
            valid_people.append(person)
        except Exception as e:
            invalid_rows.append(
                RowError(
                    row_number=row_num,
                    field=None,
                    message=f"Schema validation error: {e}",
                    raw_data=row,
                )
            )

    return ValidationSummary(
        valid_people=valid_people,
        invalid_rows=invalid_rows,
        issues=issues,
        warnings=warnings,
    )
