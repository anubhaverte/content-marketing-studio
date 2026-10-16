"""Tests for CSV loading, encoding handling, column guessing, attendee validation, and error reporting."""
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import SAMPLE_DATA
from app.data.csv_loader import (
    CsvLoadResult,
    RowError,
    guess_column_mapping,
    load_people_csv,
    parse_csv_text,
)
from app.data.validator import ValidationSummary, validate_people
from app.main import app
from app.spec.schema import Person

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests: CSV Loader
# ---------------------------------------------------------------------------

def test_load_valid_csv():
    """Valid CSV content is parsed into row dictionaries with guessed mapping."""
    content = (
        "Full Name,Role,Team,Email,ID\n"
        "Alice Smith,organizer,Design,alice@example.com,ORG-001\n"
        "Bob Jones,participant,Dev,bob@example.com,PAR-002\n"
    )
    result = load_people_csv(content)
    assert len(result.raw_rows) == 2
    assert result.column_mapping["name"] == "Full Name"
    assert result.column_mapping["role"] == "Role"
    assert result.raw_rows[0]["name"] == "Alice Smith"
    assert result.raw_rows[0]["role"] == "organizer"
    assert result.raw_rows[1]["id"] == "PAR-002"
    assert len(result.errors) == 0


def test_missing_required_name_header():
    """CSV missing a name column reports error for missing name header."""
    content = "Role,Team,Email,ID\norganizer,Design,alice@example.com,ORG-001\n"
    result = load_people_csv(content)
    assert any(e.field == "name" for e in result.errors)
    assert any("missing required 'name' column" in e.message.lower() for e in result.errors)


def test_empty_file():
    """Completely empty file returns appropriate error."""
    result = load_people_csv("")
    assert len(result.raw_rows) == 0
    assert len(result.errors) > 0
    assert "empty" in result.errors[0].message.lower() or "no header" in result.errors[0].message.lower()


def test_blank_rows_handling():
    """Blank or whitespace-only rows are cleanly skipped while preserving valid row indexing."""
    content = (
        "Full Name,Role,ID\n"
        "Alice,organizer,1\n"
        "\n"
        "   \n"
        ",,\n"
        "Bob,participant,2\n"
    )
    result = load_people_csv(content)
    assert len(result.raw_rows) == 2
    assert result.raw_rows[0]["name"] == "Alice"
    assert result.raw_rows[0]["_row_num"] == 2
    assert result.raw_rows[1]["name"] == "Bob"
    # Row 6 is Bob because rows 3, 4, 5 are blank/empty
    assert result.raw_rows[1]["_row_num"] == 6


def test_utf8_bom_handling():
    """UTF-8 BOM is transparently stripped from header names."""
    content_bytes = "\ufeffFull Name,Role,ID\nAlice,organizer,1\n".encode("utf-8")
    result = load_people_csv(content_bytes)
    assert result.headers[0] == "Full Name"
    assert "name" in result.column_mapping
    assert result.column_mapping["name"] == "Full Name"
    assert result.raw_rows[0]["name"] == "Alice"


def test_duplicate_headers():
    """Duplicate header names in CSV are detected and warned."""
    content = "Name,Role,Name,ID\nAlice,participant,AliceDup,01\n"
    result = load_people_csv(content)
    assert any("duplicate csv headers" in w.lower() for w in result.warnings)


def test_semicolon_delimited_csv():
    """Sniffer detects semicolon delimiters."""
    content = "Name;Role;ID\nAlice;organizer;ORG01\nBob;participant;P02\n"
    result = load_people_csv(content)
    assert len(result.raw_rows) == 2
    assert result.raw_rows[0]["name"] == "Alice"


# ---------------------------------------------------------------------------
# Unit tests: Validation & Person Creation
# ---------------------------------------------------------------------------

def test_missing_name_row_reported_as_invalid():
    """A row with missing/empty name is recorded in invalid_rows and not discarded silently."""
    rows = [
        {"_row_num": 2, "name": "Alice", "role": "organizer", "id": "1"},
        {"_row_num": 3, "name": "", "role": "participant", "id": "2"},
        {"_row_num": 4, "name": "   ", "role": "participant", "id": "3"},
        {"_row_num": 5, "name": "Bob", "role": "mentor", "id": "4"},
    ]
    summary = validate_people(rows)
    assert len(summary.valid_people) == 2
    assert summary.valid_people[0].name == "Alice"
    assert summary.valid_people[1].name == "Bob"
    assert len(summary.invalid_rows) == 2
    assert summary.invalid_rows[0].row_number == 3
    assert summary.invalid_rows[0].field == "name"
    assert summary.invalid_rows[1].row_number == 4
    assert summary.issues["missing_names"] == 2


def test_unknown_roles_flagged():
    """Unknown roles are counted and recorded as warnings without dropping the attendee."""
    rows = [
        {"_row_num": 2, "name": "Alice", "role": "VIP Guest", "id": "1"},
        {"_row_num": 3, "name": "Bob", "role": "Staff", "id": "2"},
    ]
    summary = validate_people(rows)
    assert len(summary.valid_people) == 2
    assert summary.issues["unknown_roles"] == 2
    assert any("VIP Guest" in w for w in summary.warnings)
    assert any("Staff" in w for w in summary.warnings)


def test_duplicate_person_ids():
    """Duplicate IDs are flagged and warned while preserving both records."""
    rows = [
        {"_row_num": 2, "name": "Alice", "role": "participant", "id": "DUP-01"},
        {"_row_num": 3, "name": "Bob", "role": "participant", "id": "DUP-01"},
        {"_row_num": 4, "name": "Charlie", "role": "participant", "id": "DUP-02"},
    ]
    summary = validate_people(rows)
    assert len(summary.valid_people) == 3
    assert summary.issues["duplicate_ids"] == 1
    assert any("Duplicate ID 'DUP-01'" in w for w in summary.warnings)


def test_validation_against_sample_messy_csv():
    """Run full messy sample dataset against loader and validator and verify against expected_issues."""
    csv_path = SAMPLE_DATA / "people_messy.csv"
    expected_path = SAMPLE_DATA / "expected_issues.json"

    if not csv_path.exists() or not expected_path.exists():
        pytest.skip("Sample data files not present")

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    load_res = load_people_csv(csv_path)
    assert len(load_res.raw_rows) == expected["total_rows"]

    summary = validate_people(load_res.raw_rows)
    assert len(summary.valid_people) == expected["total_rows"]
    assert summary.issues["unknown_roles"] == expected["unknown_roles"]
    assert summary.issues["duplicate_ids"] == expected["duplicate_id_rows"]
    assert summary.issues["very_long_names"] == expected["very_long_names"]
    assert summary.issues["single_word_names"] == expected["single_word_names"]
    assert summary.issues["very_short_names"] == expected["very_short_names"]
    assert summary.issues["accented_names"] == expected["accented_names"]
    assert summary.issues["messy_whitespace_or_case"] == expected["messy_whitespace_or_case"]
    assert summary.issues["missing_photo"] == expected["missing_photo"]
    assert summary.issues["missing_team"] == expected["missing_team"]
    assert summary.issues["missing_id"] == expected["missing_id"]


# ---------------------------------------------------------------------------
# API Integration & Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_upload_valid_csv():
    """POST /data/upload parses real CSV and returns valid DataSummary."""
    csv_bytes = b"Full Name,Role,Team,Email,ID\nAlice,organizer,Design,alice@test.com,1\nBob,participant,Dev,bob@test.com,2\n"
    files = {"file": ("attendees.csv", io.BytesIO(csv_bytes), "text/csv")}

    response = client.post("/data/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["people_loaded"] == 2
    assert data["column_mapping"]["name"] == "Full Name"
    assert data["mock"] is True  # Preserves default mock contract flag


def test_api_upload_with_real_flag():
    """POST /data/upload?mock=false returns real summary with mock=False."""
    csv_bytes = b"Full Name,Role,Team,Email,ID\nAlice,organizer,Design,alice@test.com,1\n"
    files = {"file": ("attendees.csv", io.BytesIO(csv_bytes), "text/csv")}

    response = client.post("/data/upload?mock=false", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is False
    assert data["people_loaded"] == 1


def test_api_upload_empty_csv_returns_400():
    """POST /data/upload with empty CSV returns 400 Bad Request."""
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    response = client.post("/data/upload", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower() or "no readable headers" in response.json()["detail"].lower()


def test_api_upload_missing_name_returns_400():
    """POST /data/upload with missing name column returns 400."""
    csv_bytes = b"Role,Team,Email,ID\norganizer,Core,admin@test.com,1\n"
    files = {"file": ("noname.csv", io.BytesIO(csv_bytes), "text/csv")}
    response = client.post("/data/upload", files=files)
    assert response.status_code == 400
    assert "name" in response.json()["detail"].lower()


def test_api_upload_explicit_mock_mode():
    """POST /data/upload?mock=true explicitly returns mock summary."""
    csv_bytes = b"Name,Role\nPerson1,participant\nPerson2,mentor\n"
    files = {"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")}
    response = client.post("/data/upload?mock=true", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["mock"] is True
    assert data["people_loaded"] == 2
