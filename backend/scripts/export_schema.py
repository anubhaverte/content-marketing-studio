"""Export Pydantic models to JSON Schema files in docs/schemas/.

Deterministic output: indent=2, sort_keys=True, UTF-8, LF line endings, trailing newline.
Only Person 1 runs/updates this script.
"""
import json
import sys
from pathlib import Path

# Add backend/ to sys.path so app can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


def export_all() -> None:
    """Generate and write all JSON Schema files to docs/schemas/."""
    out_dir = ROOT / "docs" / "schemas"
    out_dir.mkdir(parents=True, exist_ok=True)

    for filename, model in sorted(SCHEMAS.items()):
        schema_dict = model.model_json_schema()
        # Deterministic formatting
        content = json.dumps(schema_dict, indent=2, sort_keys=True) + "\n"
        # Ensure LF line endings
        content = content.replace("\r\n", "\n")

        target = out_dir / filename
        target.write_bytes(content.encode("utf-8"))
        print(f"Exported: {target.relative_to(ROOT)}")


if __name__ == "__main__":
    export_all()
