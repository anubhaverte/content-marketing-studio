"""Generate a deliberately messy 250-person test dataset (all names are fictional).

Run from backend/:  python scripts/make_sample_data.py

Writes (into the repo-root sample_data/ folder by default):
  people_messy.csv        250 rows with tricky cases
  expected_issues.json    exact counts of every injected problem (ground truth for later tests)
  photos/                 generated placeholder photos (git-ignored, re-created by this script)

The random seed is fixed, so the CSV is identical on every run.
"""
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.config import SAMPLE_DATA

SEED = 42
TOTAL = 250
GOOD_ROLES = ("participant", "organizer", "mentor")
BAD_ROLES = ["Particpant", "Mentr", "guest", "Organiser", "staff"]

FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Diya", "Karthik", "Meera", "Arjun", "Isha",
         "Kabir", "Neha", "Siddharth", "Riya", "Aditya", "Pooja", "Manav", "Tanvi", "Yash", "Sneha",
         "Harsh", "Kavya", "Nikhil", "Shruti", "Dhruv", "Aisha", "Varun", "Pallavi", "Rahul", "Simran"]
LAST = ["Shah", "Patel", "Sharma", "Iyer", "Mehta", "Reddy", "Nair", "Desai", "Gupta", "Joshi",
        "Verma", "Kulkarni", "Bose", "Chopra", "Rao", "Menon", "Trivedi", "Pandey", "Saxena", "Bhatt"]
LONG_PARTS = ["Venkata", "Subramaniam", "Ramakrishnan", "Narayanan", "Chandrasekhar", "Lakshmi",
              "Padmanabhan", "Viswanathan", "Gopalakrishnan", "Satyanarayana", "Balasubramanian"]
ACCENT_FIRST = ["Ananyá", "Rénu", "Zoë", "Sérena", "Amélie", "Jósé", "Ísha", "Dévika", "Özge", "Mónica"]
SHORT_NAMES = ["Om", "Jo", "Ai", "Ria", "Eka", "Dev"]
TEAMS = [f"Team {n}" for n in ("Alpha", "Bravo", "Cosmos", "Delta", "Echo", "Falcon", "Gamma", "Helix",
                                "Ion", "Jupiter", "Kilo", "Lumen", "Mercury", "Nova", "Orbit", "Pulse",
                                "Quark", "Rocket", "Sigma", "Titan", "Umbra", "Vertex", "Warp", "Xenon", "Zephyr")]
PALETTE = [(31, 111, 235), (217, 72, 15), (47, 158, 68), (134, 46, 156), (224, 49, 49), (8, 127, 140)]


def _initials(name: str) -> str:
    parts = [p for p in name.replace(",", " ").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _make_photo(path: Path, name: str, color, size=(600, 720), blur=False) -> None:
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    font = _font(size[1] // 3)
    text = _initials(name)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((size[0] - (box[2] - box[0])) / 2 - box[0], (size[1] - (box[3] - box[1])) / 2 - box[1]),
              text, fill="white", font=font)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=14))
    img.save(path, "JPEG", quality=88)


def _long_name(rng: random.Random) -> str:
    """Build a name of 40 to 50 characters."""
    while True:
        parts = rng.sample(LONG_PARTS, rng.choice([3, 4])) + [rng.choice(LAST)]
        name = " ".join(parts)
        if 40 <= len(name) <= 50:
            return name


def generate(out_dir: Path = SAMPLE_DATA, with_photos: bool = True) -> dict:
    """Write the dataset and return the expected-issues dictionary."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    # 1) Base people: unique normal names, IDs, roles, teams
    names = []
    seen = set()
    while len(names) < TOTAL:
        n = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if n not in seen:
            seen.add(n)
            names.append(n)
    rows = []
    for i, name in enumerate(names):
        rows.append({
            "name": name,
            "role": rng.choices(GOOD_ROLES, weights=[80, 12, 8])[0],
            "id": f"HK25-{i + 1:04d}",
            "team": rng.choice(TEAMS),
            "email": f"person{i + 1:04d}@example.com",
            "photo": f"photo_{i + 1:04d}.jpg",
        })

    # 2) Pick disjoint rows for the name / role / duplicate-ID problems
    order = list(range(TOTAL))
    rng.shuffle(order)

    def take(n: int) -> list[int]:
        picked, order[:] = order[:n], order[n:]
        return picked

    long_rows, single_rows, short_rows = take(12), take(8), take(6)
    accent_rows, messy_rows, badrole_rows, dup_rows = take(10), take(15), take(10), take(10)

    for i in long_rows:
        rows[i]["name"] = _long_name(rng)
    for i in single_rows:
        rows[i]["name"] = rng.choice(FIRST)                      # one word, 4+ letters
    for i, nm in zip(short_rows, SHORT_NAMES):
        rows[i]["name"] = nm                                     # 2 to 3 letters
    for i in accent_rows:
        rows[i]["name"] = f"{rng.choice(ACCENT_FIRST)} {rng.choice(LAST)}"
    for k, i in enumerate(messy_rows):
        base = rows[i]["name"]
        rows[i]["name"] = [f"  {base.lower()}  ", base.upper(), base.lower(), f" {base}"][k % 4]
    for k, i in enumerate(badrole_rows):
        rows[i]["role"] = BAD_ROLES[k % len(BAD_ROLES)]

    # 3) Missing values (independent of the name problems)
    all_idx = list(range(TOTAL))
    missing_photo = rng.sample(all_idx, 50)
    missing_team = rng.sample(all_idx, 15)
    missing_id = rng.sample([i for i in all_idx if i not in set(dup_rows)], 10)
    for i in missing_photo:
        rows[i]["photo"] = ""
    for i in missing_team:
        rows[i]["team"] = ""
    for i in missing_id:
        rows[i]["id"] = ""
    # Duplicate IDs: these rows reuse the ID of an earlier row that still has an ID
    for i in sorted(dup_rows):
        candidates = [j for j in range(i) if j not in set(missing_id) and j not in set(dup_rows)]
        rows[i]["id"] = rows[rng.choice(candidates)]["id"]

    # 4) Special photo cases, chosen among rows that have a photo
    with_photo = [i for i in all_idx if rows[i]["photo"]]
    rng.shuffle(with_photo)
    special = {"tiny": with_photo[:5], "blurred": with_photo[5:10],
               "huge": with_photo[10:15], "wrong_aspect": with_photo[15:20]}

    # 5) Write the CSV (messy column names on purpose: the loader must map them in Phase 3)
    csv_path = out_dir / "people_messy.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Full Name", "Role", "ID", "Team", "Email", "Photo"])
        for r in rows:
            w.writerow([r["name"], r["role"], r["id"], r["team"], r["email"], r["photo"]])

    # 6) Photos
    if with_photos:
        photo_dir = out_dir / "photos"
        photo_dir.mkdir(exist_ok=True)
        sizes = {}
        for k, i in special.items():
            for j in i:
                sizes[j] = k
        for i in with_photo:
            kind = sizes.get(i)
            size = {"tiny": (120, 144), "huge": (3000, 3600), "wrong_aspect": (800, 600)}.get(kind, (600, 720))
            _make_photo(photo_dir / rows[i]["photo"], rows[i]["name"].strip(),
                        PALETTE[i % len(PALETTE)], size=size, blur=(kind == "blurred"))

    # 7) Ground truth
    expected = {
        "total_rows": TOTAL,
        "very_long_names": len(long_rows),
        "single_word_names": len(single_rows),
        "very_short_names": len(short_rows),
        "accented_names": len(accent_rows),
        "messy_whitespace_or_case": len(messy_rows),
        "unknown_roles": len(badrole_rows),
        "duplicate_id_rows": len(dup_rows),
        "missing_photo": len(missing_photo),
        "missing_team": len(missing_team),
        "missing_id": len(missing_id),
        "special_photos": {k: [rows[i]["photo"] for i in v] for k, v in special.items()},
    }
    (out_dir / "expected_issues.json").write_text(json.dumps(expected, indent=2), encoding="utf-8")
    return expected


if __name__ == "__main__":
    result = generate()
    print(f"Wrote {result['total_rows']} rows to {SAMPLE_DATA}")
    for k, v in result.items():
        if not isinstance(v, (dict, list)):
            print(f"  {k}: {v}")
