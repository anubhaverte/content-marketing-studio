"""The sample data generator injects exactly the problems it says it does."""
import csv
import json

import pytest
from PIL import Image

import make_sample_data

GOOD_ROLES = {"participant", "organizer", "mentor"}


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("sample")
    expected = make_sample_data.generate(out, with_photos=True)
    with open(out / "people_messy.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return out, expected, rows


def test_expected_file_matches_return_value(dataset):
    out, expected, _ = dataset
    assert json.loads((out / "expected_issues.json").read_text(encoding="utf-8")) == expected


def test_has_250_rows(dataset):
    _, expected, rows = dataset
    assert len(rows) == 250 == expected["total_rows"]


def test_counts_recomputed_from_csv_match_ground_truth(dataset):
    """Count each problem again from the CSV itself, independent of the generator."""
    _, expected, rows = dataset
    names = [r["Full Name"] for r in rows]
    stripped = [n.strip() for n in names]

    seen, dup = set(), 0
    for r in rows:
        if r["ID"]:
            dup += r["ID"] in seen
            seen.add(r["ID"])

    assert sum(len(n) >= 40 for n in stripped) == expected["very_long_names"]
    assert sum(" " not in n and len(n) >= 4 for n in stripped) == expected["single_word_names"]
    assert sum(len(n) <= 3 for n in stripped) == expected["very_short_names"]
    assert sum(any(ord(c) > 127 for c in n) for n in names) == expected["accented_names"]
    assert sum(n != n.strip() or n.isupper() or n.islower() for n in names) == expected["messy_whitespace_or_case"]
    assert sum(r["Role"].strip().lower() not in GOOD_ROLES for r in rows) == expected["unknown_roles"]
    assert dup == expected["duplicate_id_rows"]
    assert sum(r["Photo"] == "" for r in rows) == expected["missing_photo"]
    assert sum(r["Team"] == "" for r in rows) == expected["missing_team"]
    assert sum(r["ID"] == "" for r in rows) == expected["missing_id"]


def test_long_names_are_40_to_50_chars(dataset):
    _, _, rows = dataset
    long_names = [r["Full Name"] for r in rows if len(r["Full Name"].strip()) >= 40]
    assert long_names and all(40 <= len(n) <= 50 for n in long_names)


def test_role_mix_is_mostly_participants(dataset):
    _, _, rows = dataset
    assert sum(r["Role"] == "participant" for r in rows) > 150


def test_photos_exist_and_special_cases_have_right_shape(dataset):
    out, expected, rows = dataset
    named = {r["Photo"] for r in rows if r["Photo"]}
    assert len(named) == 200
    assert all((out / "photos" / n).exists() for n in named)
    special = expected["special_photos"]
    assert Image.open(out / "photos" / special["tiny"][0]).size == (120, 144)
    assert Image.open(out / "photos" / special["huge"][0]).size == (3000, 3600)
    assert Image.open(out / "photos" / special["wrong_aspect"][0]).size == (800, 600)
    assert Image.open(out / "photos" / special["blurred"][0]).size == (600, 720)


def test_generator_is_deterministic(tmp_path):
    make_sample_data.generate(tmp_path / "a", with_photos=False)
    make_sample_data.generate(tmp_path / "b", with_photos=False)
    assert (tmp_path / "a" / "people_messy.csv").read_bytes() == (tmp_path / "b" / "people_messy.csv").read_bytes()
    assert (tmp_path / "a" / "expected_issues.json").read_bytes() == (tmp_path / "b" / "expected_issues.json").read_bytes()
