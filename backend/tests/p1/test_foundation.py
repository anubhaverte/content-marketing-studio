"""Tests for conflict-proof team foundation and repository rules."""
import importlib
import json
import pkgutil
import subprocess
from pathlib import Path

import pytest

from app.config import ROOT
from app.main import app
from app.spec.paths import asset_path
from scripts.check_ownership import owner_of


def test_gitattributes_and_editorconfig_exist():
    assert (ROOT / ".gitattributes").exists()
    assert (ROOT / ".editorconfig").exists()


def test_owners_json_structure_and_coverage():
    owners_path = ROOT / "docs" / "OWNERS.json"
    assert owners_path.exists()
    rules = json.loads(owners_path.read_text(encoding="utf-8"))
    assert isinstance(rules, list)

    valid_owners = {"p1", "p2", "p3", "p4"}
    for rule in rules:
        assert "path" in rule and "owner" in rule
        assert rule["owner"] in valid_owners

    # Check git ls-files if git is available
    try:
        git_files = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("git not available in environment")

    for f in git_files:
        f_norm = f.strip().replace("\\", "/")
        if f_norm:
            ow = owner_of(f_norm, rules)
            assert ow is not None, f"File {f_norm} is unowned in docs/OWNERS.json"


def test_owner_of_longest_prefix_and_exact_files():
    rules = [
        {"path": "backend/", "owner": "p1"},
        {"path": "backend/app/", "owner": "p1"},
        {"path": "backend/app/api/routes_render.py", "owner": "p2"},
        {"path": "docs/", "owner": "p1"},
        {"path": "docs/p2/", "owner": "p2"},
    ]
    # Exact file overrides folder
    assert owner_of("backend/app/api/routes_render.py", rules) == "p2"
    assert owner_of("backend/app/api/routes_meta.py", rules) == "p1"
    # Subfolder overrides parent folder
    assert owner_of("docs/p2/a.md", rules) == "p2"
    assert owner_of("docs/DESIGN_SPEC.md", rules) == "p1"
    # Unknown path
    assert owner_of("some/random/untracked/file.txt", rules) is None


def test_router_auto_discovery():
    from app import api as api_pkg

    # Check every routes_*.py in app.api defines router and its routes are in app
    openapi_paths = set(app.openapi()["paths"].keys())
    for module_info in pkgutil.iter_modules(api_pkg.__path__):
        if module_info.name.startswith("routes_"):
            mod = importlib.import_module(f"app.api.{module_info.name}")
            assert hasattr(mod, "router"), f"{module_info.name} missing 'router' attribute"
            for r in mod.router.routes:
                assert r.path in openapi_paths, f"Route {r.path} from {module_info.name} not in app"


def test_requirements_split_and_lock_not_tracked():
    req_path = ROOT / "backend" / "requirements.txt"
    assert req_path.exists()
    content = req_path.read_text(encoding="utf-8")
    assert "fastapi" in content
    assert (ROOT / "backend" / "requirements" / "base.txt").exists()
    assert (ROOT / "backend" / "requirements" / "p1.txt").exists()
    assert (ROOT / "backend" / "requirements" / "p2.txt").exists()
    assert (ROOT / "backend" / "requirements" / "p4.txt").exists()

    # Assert requirements.lock.txt is not tracked
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files", "backend/requirements.lock.txt"],
            cwd=ROOT,
            text=True,
        ).strip()
        assert tracked == "", "backend/requirements.lock.txt should not be tracked by git"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass


def test_asset_path_validation():
    # Valid relative path
    resolved = asset_path("assets/logos/svnit.svg")
    assert resolved.exists()
    assert resolved.is_file()

    # Rejection of invalid paths
    with pytest.raises(ValueError):
        asset_path("/abs/path")
    with pytest.raises(ValueError):
        asset_path("C:/path")
    with pytest.raises(ValueError):
        asset_path("../escape/file.svg")
    with pytest.raises(ValueError):
        asset_path("assets/../secrets.txt")
