"""Run all project validation scripts in order and summarize their results."""

import subprocess
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
SCRIPTS = (
    "validate_layouts.py",
    "check_contrast.py",
    "check_roles_bw.py",
)


def main() -> int:
    results = []
    for script_name in SCRIPTS:
        script_path = Path(__file__).resolve().parent / script_name
        print(f"\n=== {script_name} ===", flush=True)
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=_repo_root,
            check=False,
        )
        results.append((script_name, result.returncode == 0))

    print("\n=== Final summary ===")
    print(f"{'Script':<24} Result")
    print("-" * 34)
    for script_name, passed in results:
        print(f"{script_name:<24} {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
