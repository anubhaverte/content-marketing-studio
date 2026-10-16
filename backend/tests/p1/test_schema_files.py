"""Tests verifying that docs/schemas/*.json match current Pydantic models."""
import json
from pathlib import Path
import pytest

from app.brief.schema import Brief
from app.config import ROOT
from app.spec.schema import DesignSpec, Layout, PatchOp, Person, Theme

SCHEMAS = {
    "layout.schema.json": Layout,
    "theme.schema.json": Theme,
    "design_spec.schema.json": DesignSpec,
    "brief.schema.json": Brief,
    "person.schema.json": Person,
    "patch_op.schema.json": PatchOp,
}


def test_schema_files_exist_and_match_models():
    """Each JSON Schema file on disk in docs/schemas/ must exactly match the model's schema."""
    schemas_dir = ROOT / "docs" / "schemas"
    assert schemas_dir.is_dir(), f"Schema directory not found: {schemas_dir}"

    for filename, model in SCHEMAS.items():
        schema_file = schemas_dir / filename
        assert schema_file.exists(), f"Missing schema file: {schema_file}"

        disk_data = json.loads(schema_file.read_text(encoding="utf-8"))
        generated_data = model.model_json_schema()

        assert disk_data == generated_data, (
            f"Schema file {filename} is out of sync with {model.__name__}. "
            f"Run 'python scripts/export_schema.py' to update it."
        )


def test_schema_files_line_endings():
    """Schema files should have LF line endings and end with a single newline."""
    schemas_dir = ROOT / "docs" / "schemas"
    for filename in SCHEMAS:
        raw_bytes = (schemas_dir / filename).read_bytes()
        assert b"\r\n" not in raw_bytes, f"{filename} contains CRLF line endings"
        assert raw_bytes.endswith(b"\n"), f"{filename} does not end with a newline"
