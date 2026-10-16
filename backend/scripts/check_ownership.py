"""Check that changed files belong to the specified owner before pushing.

Usage:
    python scripts/check_ownership.py --owner p1 [--base origin/main]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


def find_repo_root() -> Path:
    """Find the root directory of the git repository."""
    # This script is at backend/scripts/check_ownership.py
    # So repo root is 2 levels up from backend/scripts/
    return Path(__file__).resolve().parents[2]


def load_owners(repo_root: Path) -> list[dict]:
    """Load the ownership rules from docs/OWNERS.json."""
    owners_file = repo_root / "docs" / "OWNERS.json"
    if not owners_file.exists():
        raise FileNotFoundError(f"Missing ownership file: {owners_file}")
    with open(owners_file, "r", encoding="utf-8") as f:
        return json.load(f)


def owner_of(path: str, rules: list[dict]) -> Optional[str]:
    """Return the owner of a given repo-relative path using longest-prefix match.

    A path ending with '/' is treated as a folder prefix rule.
    Otherwise it is treated as an exact-file match.
    The longest matching rule wins.
    """
    normalized_path = path.replace("\\", "/").strip()
    best_len = -1
    best_owner = None

    for rule in rules:
        rule_path = rule["path"]
        if rule_path.endswith("/"):
            if normalized_path.startswith(rule_path) and len(rule_path) > best_len:
                best_len = len(rule_path)
                best_owner = rule["owner"]
        else:
            if normalized_path == rule_path and len(rule_path) > best_len:
                best_len = len(rule_path)
                best_owner = rule["owner"]

    return best_owner


def get_default_base(repo_root: Path) -> str:
    """Determine the default git base: origin/main if it exists, else main."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--verify", "origin/main"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return "origin/main"
    except Exception:
        pass
    return "main"


def get_changed_files(repo_root: Path, base_ref: str) -> list[str]:
    """Gather changed files compared to base_ref plus untracked files."""
    changed = set()

    # Changed files compared to base
    try:
        diff_out = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        for f in diff_out:
            f = f.strip().replace("\\", "/")
            if f:
                changed.add(f)
    except subprocess.CalledProcessError:
        pass

    # Untracked files
    try:
        untracked_out = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        for f in untracked_out:
            f = f.strip().replace("\\", "/")
            if f:
                changed.add(f)
    except subprocess.CalledProcessError:
        pass

    return sorted(changed)


def main() -> int:
    """Check ownership of changed and untracked files."""
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(description="Check git file ownership against docs/OWNERS.json")
    parser.add_argument("--owner", required=True, choices=["p1", "p2", "p3", "p4"], help="Current developer role")
    parser.add_argument("--base", default=None, help="Base git ref to compare against (default: origin/main or main)")
    args = parser.parse_args()

    base_ref = args.base if args.base else get_default_base(repo_root)
    rules = load_owners(repo_root)
    changed_files = get_changed_files(repo_root, base_ref)

    if not changed_files:
        print("OK: No changed or untracked files.")
        return 0

    not_owned = []
    unowned = []

    print(f"Checking ownership for {len(changed_files)} file(s) against base '{base_ref}' (expected owner: {args.owner}):\n")
    for file_path in changed_files:
        file_owner = owner_of(file_path, rules)
        print(f"  [{file_owner or 'UNOWNED'}] {file_path}")
        if not file_owner:
            unowned.append(file_path)
        elif file_owner != args.owner:
            not_owned.append((file_path, file_owner))

    failed = False
    if unowned:
        failed = True
        print("\nUNOWNED FILES (must be added to docs/OWNERS.json):")
        for f in unowned:
            print(f"  - {f}")

    if not_owned:
        failed = True
        print("\nFILES YOU DO NOT OWN:")
        for f, actual_owner in not_owned:
            print(f"  - {f} (owned by {actual_owner})")

    if failed:
        print("\nFAILED: Ownership check failed. Do not commit or push files outside your ownership.")
        return 1

    print("\nOK: All changed files belong to " + args.owner)
    return 0


if __name__ == "__main__":
    sys.exit(main())
