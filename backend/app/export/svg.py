"""Save SVG text to a file (the editable vector output)."""
from pathlib import Path


def save_svg(svg_text: str, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg_text, encoding="utf-8")
    return out_path
