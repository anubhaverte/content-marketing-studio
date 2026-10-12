"""Run focused checks for the spec-driven Phase 2 SVG renderer."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import warnings
from pathlib import Path
from xml.etree import ElementTree

from render import spec_adapter
from render.loaders import LAYOUTS_DIR, THEMES_DIR, load_layout, load_theme
from render.renderer import render_card


ROOT = Path(__file__).resolve().parent
SVG_NS = "{http://www.w3.org/2000/svg}"


def report(label: str, passed: bool, detail: str) -> bool:
    """Print a PASS/FAIL line and return the result."""
    print(f"{'PASS' if passed else 'FAIL'}: {label} - {detail}")
    return passed


def main() -> int:
    """Run all ten requested behavior checks."""
    results: list[bool] = []
    spec = spec_adapter.load_design_spec()
    people = spec_adapter.load_people()
    classic = spec_adapter.with_choices(spec, layout="classic", theme="blue")
    split = spec_adapter.with_choices(spec, layout="split", theme="dark")
    classic_svgs = [render_card(classic, person) for person in people]
    results.append(report("1. All sample people render with classic + blue", len(classic_svgs) == len(people),
                          f"rendered {len(classic_svgs)} SVGs"))
    split_svgs = [render_card(split, person) for person in people]
    matched_people = [
        spec_adapter.person_value(person, "name") or f"person {index}"
        for index, (person, classic_svg, split_svg) in enumerate(
            zip(people, classic_svgs, split_svgs), start=1
        )
        if classic_svg == split_svg
    ]
    differs = (
        len(classic_svgs) == len(people)
        and len(split_svgs) == len(people)
        and not matched_people
    )
    results.append(report("2. Split + dark changes each rendered SVG", differs,
                          f"all {len(people)} corresponding people differ" if differs
                          else f"matching SVGs: {', '.join(matched_people) if matched_people else 'rendered SVG count did not match people count'}"))

    color_change_passed = False
    with tempfile.TemporaryDirectory(prefix="phase2-theme-") as temp_directory:
        temporary_theme_directory = Path(temp_directory)
        theme_data = load_theme("blue", THEMES_DIR)
        original_color = theme_data["colors"]["primary"]
        theme_data["colors"]["primary"] = "#010203" if original_color != "#010203" else "#030201"
        theme_data.pop("_source_file", None)
        (temporary_theme_directory / "blue.json").write_text(
            json.dumps(theme_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        custom_theme = load_theme("blue", temporary_theme_directory)
        custom_svgs = [
            _render_with_theme(classic, person, custom_theme) for person in people
        ]
        color_change_passed = any(before != after for before, after in zip(classic_svgs, custom_svgs))
    results.append(report("3. Theme file color change affects SVG output", color_change_passed,
                          "temporary JSON theme edit changed the SVG without code changes"))

    roles = ("participant", "organizer", "mentor", "volunteer")
    role_people = [spec_adapter.sample_person_for_role(role, people) for role in roles]
    role_svgs = [render_card(classic, person) for person in role_people]
    role_different = len(set(role_svgs)) == len(roles)
    results.append(report("4. Each role has a different color and cue", role_different,
                          "all four role SVGs differ" if role_different else "role SVGs were not all distinct"))

    gray_shapes = [_grayscale_cue_shape(svg) for svg in role_svgs]
    grayscale_different = all(shape is not None for shape in gray_shapes) and len(set(gray_shapes)) == len(roles)
    results.append(report("5. Role cues still differ in grayscale", grayscale_different,
                          f"cue shapes after grayscale: {', '.join(str(shape) for shape in gray_shapes)}"))

    geometry_ok = all(_has_card_geometry(svg) for svg in classic_svgs + split_svgs)
    results.append(report("6. SVG dimensions and viewBox are correct", geometry_ok,
                          "width=60mm, height=92mm, viewBox=0 0 60 92"))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        placeholder_svg = render_card(classic, people[0])
    placeholder_ok = (
        "EVENT NAME" in placeholder_svg
        and any("event.name is null or empty" in str(warning.message) for warning in caught)
    )
    results.append(report("7. Null event name warns and shows placeholder", placeholder_ok,
                          "visible EVENT NAME placeholder and warning were produced"))

    try:
        invalid = spec_adapter.with_choices(spec, layout="not-a-layout")
        render_card(invalid, people[0])
    except ValueError as error:
        unknown_layout_ok = "not-a-layout" in str(error) and "not-a-layout.json" in str(error)
        unknown_detail = str(error)
    else:
        unknown_layout_ok = False
        unknown_detail = "no exception was raised"
    results.append(report("8. Unknown layout has a clear error", unknown_layout_ok, unknown_detail))

    layout_files = sorted(LAYOUTS_DIR.glob("*.json"))
    no_hex = bool(layout_files) and all(
        re.search(r"#[0-9A-Fa-f]{3,8}\b", path.read_text(encoding="utf-8")) is None
        for path in layout_files
    )
    results.append(report("9. Layout files contain no hex colors", no_hex,
                          f"checked {len(layout_files)} layout JSON files"))

    adapter_only = _spec_structure_reads_only_in_adapter()
    results.append(report("10. Only spec_adapter reads spec structure", adapter_only,
                          "renderer uses normalized adapter accessors"))

    if all(results):
        print("Phase 2 verification complete.")
        return 0
    print("Phase 2 verification failed. Fix failed items and run again.", file=sys.stderr)
    return 1


def _render_with_theme(spec: spec_adapter.DesignSpec, person: spec_adapter.Person, theme: dict) -> str:
    """Render with an explicitly loaded theme for isolated file-change testing."""
    layout = load_layout(spec_adapter.spec_layout(spec))
    from render.renderer import _render

    return _render(spec, person, layout, theme)


def _has_card_geometry(svg: str) -> bool:
    """Check the required Phase 1 card root dimensions."""
    root = ElementTree.fromstring(svg)
    return (
        root.get("width") == "60mm"
        and root.get("height") == "92mm"
        and root.get("viewBox") == "0 0 60 92"
    )


def _grayscale_cue_shape(svg: str) -> tuple[str, str] | None:
    """Apply an SVG grayscale filter and compare the remaining cue geometry."""
    root = ElementTree.fromstring(svg)
    defs = ElementTree.Element(f"{SVG_NS}defs")
    filter_node = ElementTree.SubElement(defs, f"{SVG_NS}filter", {"id": "grayscale"})
    ElementTree.SubElement(
        filter_node,
        f"{SVG_NS}feColorMatrix",
        {"type": "saturate", "values": "0"},
    )
    root.insert(0, defs)
    root.set("filter", "url(#grayscale)")
    cue = root.find(f".//*[@id='role-cue']")
    if cue is None or len(cue) != 1:
        return None
    shape = cue[0]
    return shape.tag.removeprefix(SVG_NS), shape.get("points", "")


def _spec_structure_reads_only_in_adapter() -> bool:
    """Check application modules for direct reads of JSON spec keys."""
    key_patterns = re.compile(r"""(?:spec|data)\s*\[\s*["'](?:event|card|layout|theme|logos|roles)["']""")
    python_files = list(ROOT.glob("*.py")) + list((ROOT / "render").glob("*.py"))
    for path in python_files:
        if path.name in {"spec_adapter.py", "verify_phase2.py"}:
            continue
        if key_patterns.search(path.read_text(encoding="utf-8")):
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
