"""Load participant data from CSV, handle encodings, and guess column mappings.

Provides safe CSV parsing using Python's standard library csv module.
Handles UTF-8, UTF-8 BOM, delimiter sniffing, blank rows, and column aliasing.
"""
import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union


# Standard aliases mapping common CSV header names to Person fields
STANDARD_ALIASES: dict[str, str] = {
    # name
    "name": "name",
    "full name": "name",
    "fullname": "name",
    "attendee name": "name",
    "participant name": "name",
    "student name": "name",
    # role
    "role": "role",
    "type": "role",
    "category": "role",
    "designation": "role",
    "ticket type": "role",
    # id
    "id": "id",
    "identifier": "id",
    "badge id": "id",
    "roll no": "id",
    "roll_no": "id",
    "registration id": "id",
    "reg id": "id",
    "ticket id": "id",
    # team
    "team": "team",
    "team name": "team",
    "group": "team",
    "organization": "team",
    "org": "team",
    # email
    "email": "email",
    "e-mail": "email",
    "email address": "email",
    # photo
    "photo": "photo",
    "picture": "photo",
    "image": "photo",
    "photo url": "photo",
    "photo_path": "photo",
    "avatar": "photo",
    # qr_url
    "qr": "qr_url",
    "qr_url": "qr_url",
    "qr url": "qr_url",
    "qr code": "qr_url",
    "qrcode": "qr_url",
    "url": "qr_url",
}


@dataclass
class RowError:
    """Represents a row-level parsing or validation error with 1-indexed row number."""
    row_number: int
    field: Optional[str]
    message: str
    raw_data: Optional[dict[str, Any]] = None


@dataclass
class CsvLoadResult:
    """Result of parsing and mapping a participant CSV file."""
    raw_rows: list[dict[str, Any]] = field(default_factory=list)
    column_mapping: dict[str, str] = field(default_factory=dict)
    headers: list[str] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_header(header: str) -> str:
    """Normalize a header string for alias matching."""
    return header.strip().lower().replace("-", " ").replace("_", " ")


def guess_column_mapping(columns: list[str]) -> dict[str, str]:
    """Auto-guess a mapping from target fields to matched CSV column names.

    Returns a dict {target_field: csv_column_header}.
    Also includes extra unmapped columns keyed by their lowercase names.
    Known target fields: 'name', 'role', 'id', 'team', 'email', 'photo', 'qr_url'.
    """
    mapping: dict[str, str] = {}
    assigned_targets: set[str] = set()
    matched_cols: set[str] = set()

    for col in columns:
        cleaned_col = col.strip()
        norm = normalize_header(cleaned_col)
        target = STANDARD_ALIASES.get(norm)
        if target and target not in assigned_targets:
            mapping[target] = cleaned_col
            assigned_targets.add(target)
            matched_cols.add(cleaned_col)

    # For any columns not matched to standard fields, map cleaned col to col
    for col in columns:
        cleaned_col = col.strip()
        if cleaned_col not in matched_cols:
            clean_key = cleaned_col.lower().replace(" ", "_")
            if clean_key not in mapping:
                mapping[clean_key] = cleaned_col

    return mapping


def decode_csv_bytes(content_bytes: bytes) -> str:
    """Decode raw bytes handling UTF-8 BOM, UTF-8, and fallback to latin-1."""
    try:
        return content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return content_bytes.decode("latin-1", errors="replace")


def parse_csv_text(content_text: str) -> tuple[list[str], list[tuple[int, list[str]]], list[str]]:
    """Parse CSV text into raw header, indexed data rows, and warnings.

    Returns:
        (headers, list of (row_number, row_cells), warnings)
    """
    warnings: list[str] = []
    if not content_text.strip():
        return [], [], ["CSV file is completely empty"]

    # Sniff delimiter safely
    sample = content_text[:2048]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    reader = csv.reader(io.StringIO(content_text), delimiter=delimiter)
    
    headers: list[str] = []
    data_rows: list[tuple[int, list[str]]] = []
    
    header_found = False
    for physical_idx, row in enumerate(reader, start=1):
        # Skip pure whitespace / empty rows
        if not row or not any(cell.strip() for cell in row):
            continue

        if not header_found:
            headers = [h.strip() for h in row]
            header_found = True
            continue

        data_rows.append((physical_idx, list(row)))

    return headers, data_rows, warnings


def load_people_csv(
    source: Union[Path, bytes, str],
    mapping: Optional[dict[str, str]] = None,
) -> CsvLoadResult:
    """Read CSV from a path, raw bytes, or text string and apply column mapping.

    Args:
        source: File path, bytes, or CSV string content.
        mapping: Optional custom column mapping {target_field: csv_header_name}
                 or {csv_header_name: target_field}.
                 If None, guess_column_mapping will be used.

    Returns:
        CsvLoadResult containing raw_rows, column_mapping, headers, and errors.
    """
    errors: list[RowError] = []
    warnings: list[str] = []

    if isinstance(source, Path):
        if not source.exists():
            return CsvLoadResult(
                errors=[RowError(row_number=0, field=None, message=f"File not found: {source}")]
            )
        content_bytes = source.read_bytes()
        content_text = decode_csv_bytes(content_bytes)
    elif isinstance(source, bytes):
        content_text = decode_csv_bytes(source)
    else:
        content_text = str(source)

    headers, data_rows, parse_warnings = parse_csv_text(content_text)
    warnings.extend(parse_warnings)

    if not headers:
        errors.append(RowError(row_number=0, field=None, message="CSV contains no header row or is empty"))
        return CsvLoadResult(errors=errors, warnings=warnings)

    # Check for duplicate headers
    seen_headers: set[str] = set()
    dup_headers: list[str] = []
    for h in headers:
        if h in seen_headers:
            dup_headers.append(h)
        seen_headers.add(h)
    if dup_headers:
        warnings.append(f"Duplicate CSV headers detected: {', '.join(dup_headers)}")

    # Determine column mapping: format {target_field: csv_col_name}
    if mapping is not None:
        # Normalize mapping if user passed {csv_col: target_field} instead of {target: csv_col}
        # Check if keys are standard fields or csv headers
        sample_keys = set(mapping.keys())
        standard_fields = {"name", "role", "id", "team", "email", "photo", "qr_url"}
        if standard_fields.intersection(sample_keys):
            target_to_col = mapping
        else:
            # inverted: invert to target_to_col
            target_to_col = {v: k for k, v in mapping.items()}
    else:
        target_to_col = guess_column_mapping(headers)

    # Build col_to_target lookup for row processing
    col_to_target: dict[str, str] = {col: target for target, col in target_to_col.items()}

    # Verify that 'name' target is mapped and corresponds to a header in headers
    if "name" not in target_to_col or target_to_col["name"] not in headers:
        errors.append(
            RowError(
                row_number=1,
                field="name",
                message="Missing required 'name' column in CSV headers or mapping",
            )
        )

    # Map rows to dicts
    mapped_rows: list[dict[str, Any]] = []
    for row_num, cells in data_rows:
        row_dict: dict[str, Any] = {"_row_num": row_num}
        
        # Handle rows with differing number of columns
        if len(cells) != len(headers):
            warnings.append(
                f"Row {row_num} has {len(cells)} columns; expected {len(headers)} based on header"
            )

        for col_idx, col_name in enumerate(headers):
            cell_val = cells[col_idx] if col_idx < len(cells) else ""
            target_field = col_to_target.get(col_name, col_name)
            row_dict[target_field] = cell_val

        mapped_rows.append(row_dict)

    return CsvLoadResult(
        raw_rows=mapped_rows,
        column_mapping=target_to_col,
        headers=headers,
        errors=errors,
        warnings=warnings,
    )
