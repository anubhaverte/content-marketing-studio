"""Generate deterministic 250-row export test data with difficult records."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "sample_data" / "test_250.csv"
ROLES = ("participant", "organizer", "mentor", "volunteer")


def make_rows() -> list[dict[str, str]]:
    """Build 250 records covering valid, missing, duplicate, and unusual values."""
    rows = []
    for index in range(1, 251):
        rows.append({
            "id": f"P{index:03d}",
            "name": f"Sample Person {index}",
            "role": ROLES[(index - 1) % len(ROLES)],
            "photo": ("photos/tall.png", "photos/wide.png", "photos/tiny.png")[(index - 1) % 3],
        })
    rows[0]["name"] = "Alexandria-Montgomery-Wilhelmina Catherine Alexandra Penelope Beatrice O'Connell"
    rows[1]["name"] = "Cher"
    rows[2]["name"] = "Élodie Núñez"
    rows[3]["name"] = "李小龍"
    rows[4]["name"] = "名前 with, comma and \"quotes\""
    rows[5]["photo"] = ""
    rows[19]["name"] = ""
    rows[20]["role"] = "unknown"
    rows[21]["id"] = ""
    rows[24]["id"] = rows[0]["id"]
    rows[29]["photo"] = ""
    rows[42]["name"] = "Иван Петров"
    rows[99]["name"] = "Miyuki 山田"
    rows[149]["name"] = "Núria O'Connor, Jr."
    return rows


def main() -> None:
    """Write the sample CSV using UTF-8 and standard CSV escaping."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=("id", "name", "role", "photo"))
        writer.writeheader()
        writer.writerows(make_rows())
    print(f"Wrote {OUTPUT} ({len(make_rows())} rows).")


if __name__ == "__main__":
    main()
