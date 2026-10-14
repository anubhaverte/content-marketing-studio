"""Command-line entry point for loading and exporting a batch."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from export.batch import export_batch
from export.csv_loader import load_people
from export.print_sheet import export_print_sheet
from export.settings import ExportSettings, PrintSheetSettings
from render.spec_adapter import load_design_spec


def build_parser() -> argparse.ArgumentParser:
    """Create the export command-line argument parser."""
    parser = argparse.ArgumentParser(description="Export card batches or printable sheets.")
    parser.add_argument("--spec", required=True, type=Path, help="Path to the Design Spec JSON file.")
    parser.add_argument("--people", required=True, type=Path, help="Path to a CSV or JSON people file.")
    parser.add_argument("--format", choices=("svg", "pdf", "png"), default="svg")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--orientation", choices=("portrait", "landscape"), default="portrait")
    parser.add_argument("--bleed", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--sheet",
        choices=("A4", "A3"),
        help="Export cards on a printable paper sheet.",
    )
    parser.add_argument(
        "--no-crop-marks",
        action="store_false",
        dest="crop_marks",
        default=True,
        help="Omit crop marks from a print sheet.",
    )
    parser.add_argument("--landscape", action="store_true", help="Use landscape paper orientation for --sheet.")
    parser.add_argument("--out", required=True, type=Path, help="Destination ZIP file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Load inputs, export a ZIP, and print batch totals and elapsed time."""
    args = build_parser().parse_args(argv)
    started = time.perf_counter()
    try:
        spec = load_design_spec(args.spec)
        people, problems = load_people(args.people)
        if args.sheet:
            sheet_report: dict[str, object] = {}
            orientation = "landscape" if args.landscape else args.orientation
            sheet_settings = PrintSheetSettings(
                orientation=orientation,
                bleed=args.bleed,
                crop_marks=args.crop_marks,
            )
            pdf = export_print_sheet(
                spec,
                people,
                args.sheet,
                sheet_settings,
                report=sheet_report,
                skipped_rows=problems,
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_bytes(pdf)
            elapsed = time.perf_counter() - started
            totals = sheet_report["totals"]
            settings = sheet_report["settings"]
            print(
                f"{args.sheet} {orientation}: {settings['cards_per_page']} cards per page; "
                f"{totals['pages']} page(s), {totals['exported']} exported, "
                f"{totals['failed']} failed, {totals['qa_issues']} QA issues, "
                f"{len(problems)} skipped rows; "
                f"total time {elapsed:.2f}s."
            )
            if settings["gap_increased"]:
                print(f"Crop-mark clearance increased the card gap to {settings['gap_mm']:g} mm.")
            for row in problems:
                print(f"Skipped CSV row {row['row']}: {row['reason']}")
            for record in sheet_report["people"]:
                if record["status"] == "failed":
                    print(f"Skipped person {record['id'] or 'unknown'}: {record['reason']}")
            print(f"Wrote {args.out}")
            return 0
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
