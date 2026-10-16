"""Command-line entry point for loading and exporting a batch."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from export.batch import export_batch
from export.csv_loader import load_people
from export.settings import ExportSettings
from render.spec_adapter import load_design_spec


def build_parser() -> argparse.ArgumentParser:
    """Create the export command-line argument parser."""
    parser = argparse.ArgumentParser(description="Export card batches to a ZIP archive.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to the Design Spec JSON file.")
    parser.add_argument("--people", required=True, type=Path, help="Path to a CSV or JSON people file.")
    parser.add_argument("--format", choices=("svg", "pdf", "png"), default="svg")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--orientation", choices=("portrait", "landscape"), default="portrait")
    parser.add_argument("--bleed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--out", required=True, type=Path, help="Destination ZIP file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Load inputs, export a ZIP, and print batch totals and elapsed time."""
    args = build_parser().parse_args(argv)
    started = time.perf_counter()
    try:
        spec = load_design_spec(args.spec)
        people, problems = load_people(args.people)
        settings = ExportSettings(
            format=args.format,
            dpi=args.dpi,
            orientation=args.orientation,
            bleed=args.bleed,
        )
        archive = export_batch(spec, people, settings, args.out, skipped_rows=problems)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    del archive
    elapsed = time.perf_counter() - started
    failed = _failed_count(args.out)
    print(
        f"Totals: {len(people)} people, {len(people) - failed} exported, {failed} failed, "
        f"{len(problems)} skipped rows; total time {elapsed:.2f}s."
    )
    print(f"Wrote {args.out}")
    return 0


def _failed_count(path: Path) -> int:
    """Read failed card count from the newly written ZIP report."""
    import json
    import zipfile

    with zipfile.ZipFile(path) as archive:
        import io

        with archive.open("report.json") as report_file:
            report = json.load(io.TextIOWrapper(report_file, encoding="utf-8"))
    return int(report["totals"]["failed"])


if __name__ == "__main__":
    raise SystemExit(main())
