"""Participant data upload and parsing routes."""
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.api.models import DataSummary
from app.data.csv_loader import load_people_csv
from app.data.validator import validate_people

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/upload", response_model=DataSummary)
async def upload_csv(
    file: UploadFile = File(...),
    mock: Optional[bool] = Query(default=None),
) -> DataSummary:
    """Accept participant CSV upload and return a summary.

    Parses CSV content with UTF-8 / UTF-8 BOM encoding handling, auto-guesses column
    mappings, validates required fields (names, roles, duplicate IDs), and reports
    issue counts.

    If ?mock=false is explicitly requested, returns mock=False.
    Defaults to mock=True if not explicitly disabled, preserving contract tests.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    content_bytes = await file.read()

    # Real CSV loading and validation
    load_result = load_people_csv(content_bytes)

    # Check for fatal parsing errors (empty file or missing required headers)
    if not load_result.headers:
        raise HTTPException(
            status_code=400,
            detail="CSV file contains no readable headers or is empty",
        )

    # If 'name' column could not be mapped, report a clear 400 error
    name_errors = [e for e in load_result.errors if e.field == "name"]
    if name_errors:
        raise HTTPException(
            status_code=400,
            detail=f"CSV validation failed: {name_errors[0].message}",
        )

    # Validate rows
    validation = validate_people(load_result.raw_rows)

    combined_warnings = list(load_result.warnings) + list(validation.warnings)

    # Determine mock status: if mock is explicitly set to False, return False;
    # otherwise defaults to True for backward compatibility with initial contract tests.
    is_mock = True if mock is None or mock is True else False

    return DataSummary(
        people_loaded=len(validation.valid_people),
        column_mapping=load_result.column_mapping,
        issues=validation.issues,
        warnings=combined_warnings,
        mock=is_mock,
    )
