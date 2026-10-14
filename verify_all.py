"""Run pytest and all phase verification scripts in sequence."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PHASE_SCRIPTS = tuple(f"verify_phase{phase}.py" for phase in ("1", "2", "3", "4", "5a", "5b"))


def main() -> int:
    """Run every test and phase check, summarize outcomes, and return failure status."""
    commands = [
        ("pytest", [sys.executable, "-m", "pytest"]),
        *[
            (script.removesuffix(".py"), [sys.executable, str(ROOT / script)])
            for script in PHASE_SCRIPTS
        ],
    ]
    started = time.perf_counter()
    failures: list[tuple[str, str]] = []
    for label, command in commands:
        command_started = time.perf_counter()
        try:
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            result_code = None
            output = str(error)
        else:
            result_code = result.returncode
            output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        elapsed = time.perf_counter() - command_started
        passed = result_code == 0
        print(f"{'PASS' if passed else 'FAIL'}: {label} ({elapsed:.2f}s)")
        if not passed:
            failures.append((label, output or f"process exited with status {result_code}"))
            print(output or f"process exited with status {result_code}", file=sys.stderr)

    total_elapsed = time.perf_counter() - started
    print(
        f"Verification {'passed' if not failures else 'failed'}: "
        f"{len(commands) - len(failures)}/{len(commands)} checks passed; "
        f"total time {total_elapsed:.2f}s."
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
