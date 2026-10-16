"""Create a deterministic CSV of attendee records for validation testing."""

import csv
import random
import sys
from collections import Counter
from pathlib import Path

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import SAMPLE_DATA_DIR

SEED = 20261014
CSV_PATH = SAMPLE_DATA_DIR / "test_people.csv"
PHOTO_NAMES = (
    [f"portrait_{number:02d}.jpg" for number in range(1, 21)]
    + [f"tiny_{number:02d}.jpg" for number in range(1, 3)]
    + [f"huge_{number:02d}.jpg" for number in range(1, 3)]
    + [f"square_{number:02d}.jpg" for number in range(1, 3)]
    + [f"landscape_{number:02d}.jpg" for number in range(1, 3)]
    + ["broken.jpg"]
)
LONG_NAMES = [
    "Venkatasubramanian Raghunathan Iyer-Chaturvedi",
    "Anantanarayanan Subramaniam Venkataraman",
    "Krishnamurthy Balasubramanian Narayanaswamy",
    "Ramaswamy Chandrasekharan Venkatasubbaiah",
    "Srinivasan Lakshminarayanan Krishnamurthy",
    "Subramanian Venkataraman Radhakrishnan Iyer",
    "Chandrasekaran Venkatasubramanian Narayanan",
    "Balasubramanian Ramaswamy Venkateshwaran",
    "Thiruvengadam Raghunathan Subramaniam Iyer",
    "Venkataraman Krishnaswamy Chandrasekaran Rao",
]
SHORT_NAMES = ["Al", "Bo", "Cy", "De", "E", "F", "Jo", "Lu", "M", "Z"]
MULTILINGUAL_NAMES = [
    "आरव शर्मा", "अनन्या वर्मा", "विवेक पटेल", "मीरा जोशी", "कविता सिंह",
    "રવિ પટેલ", "મીરા શાહ", "જય દેસાઈ", "નીતા જોષી", "હર્ષ મહેતા",
    "Élodie Martin", "François Dubois", "Chloé Bernard", "André Moreau", "Zoë Laurent",
    "Jürgen Müller", "Müller Schäfer", "Franziska Weiß", "Björn Schneider", "Günter Fischer",
    "Lucía García", "José Martínez", "María López", "Ángel Fernández", "Inés Rodríguez",
]
ORDINARY_NAMES = [
    "Aarav Sharma", "Ananya Patel", "Rohan Mehta", "Diya Shah", "Ishaan Desai",
    "Maya Joshi", "Kabir Rao", "Sana Khan", "Arjun Nair", "Tara Iyer",
    "Neel Kulkarni", "Aditi Verma", "Rehan Qureshi", "Nisha Menon", "Dev Malhotra",
    "Kiran Reddy", "Priya Kapoor", "Omkar Patil", "Zoya Ali", "Rahul Gupta",
    "Meera Soni", "Vikram Das", "Sara Thomas", "Nikhil Bose", "Ira Chawla",
]
INVALID_ROLES = ["particpant", "Speaker", "VOLUNTEER ", "", "Participant", "mentor ", "guest", "ORGANIZER"]
TEAMS = [
    "Team Alpha", "Team Beta", "Team Gamma", "Team Delta", "Team Epsilon",
    "Team Zeta", "Team Eta", "Team Theta", "Team Iota", "Team Kappa",
]


def main() -> None:
    rng = random.Random(SEED)
    names = (
        LONG_NAMES
        + SHORT_NAMES
        + MULTILINGUAL_NAMES
        + [rng.choice(ORDINARY_NAMES) for _ in range(250 - 10 - 10 - 25)]
    )
    rng.shuffle(names)

    roles = ["participant"] * 207 + ["mentor"] * 20 + ["organizer"] * 15 + INVALID_ROLES
    rng.shuffle(roles)

    photo_names = list(PHOTO_NAMES)
    rng.shuffle(photo_names)
    photos = [""] * 15 + [photo_names[index % len(photo_names)] for index in range(235)]
    rng.shuffle(photos)

    team_values = [rng.choice(TEAMS) for _ in range(250)]
    for index in rng.sample(range(250), 10):
        team_values[index] = ""

    ids = [f"SVNIT-2026-{number:04d}" for number in range(1, 241)]
    ids.extend([""] * 10)
    rng.shuffle(ids)
    nonempty_indices = [index for index, value in enumerate(ids) if value]
    for first, second in zip(nonempty_indices[:10:2], nonempty_indices[1:10:2]):
        ids[second] = ids[first]

    rows = []
    for index, (name, role, identifier, team, photo) in enumerate(
        zip(names, roles, ids, team_values, photos), start=1
    ):
        email_name = "".join(
            char.lower() if char.isalnum() and char.isascii() else ""
            for char in name
        ) or "attendee"
        rows.append(
            {
                "name": name,
                "role": role,
                "id": identifier,
                "team": team,
                "photo": photo,
                "email": f"{email_name}.{index:03d}@example.org",
            }
        )

    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=("name", "role", "id", "team", "photo", "email"),
        )
        writer.writeheader()
        writer.writerows(rows)

    duplicate_count = sum(count - 1 for count in Counter(
        row["id"] for row in rows if row["id"]
    ).values() if count > 1)
    role_counts = Counter(row["role"] for row in rows)
    print(f"Created {CSV_PATH.name}: {len(rows)} rows (seed {SEED})")
    print(
        "Roles: "
        f"{role_counts['participant']} participant, "
        f"{role_counts['mentor']} mentor, "
        f"{role_counts['organizer']} organizer, "
        f"{sum(role_counts[role] for role in INVALID_ROLES)} invalid/unknown"
    )
    print(
        f"Edge cases: {len(LONG_NAMES)} long names, {len(SHORT_NAMES)} short names, "
        f"{len(MULTILINGUAL_NAMES)} multilingual names, "
        f"{sum(not row['photo'] for row in rows)} empty photos, "
        f"{sum(not row['team'] for row in rows)} empty teams, "
        f"{sum(not row['id'] for row in rows)} empty IDs, "
        f"5 duplicate ID pairs ({duplicate_count} extra duplicate rows)"
    )


if __name__ == "__main__":
    main()
