"""Generate small synthetic placeholder photos for photo-validation tests."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import SAMPLE_DATA_DIR

PHOTOS_DIR = SAMPLE_DATA_DIR / "photos"
NORMAL_SIZES = [(600, 800)] * 20
SPECIAL_PHOTOS = [
    ("tiny_01.jpg", (60, 80)),
    ("tiny_02.jpg", (60, 80)),
    ("huge_01.jpg", (4000, 5000)),
    ("huge_02.jpg", (4000, 5000)),
    ("square_01.jpg", (600, 600)),
    ("square_02.jpg", (600, 600)),
    ("landscape_01.jpg", (800, 600)),
    ("landscape_02.jpg", (800, 600)),
]
PALETTE = [
    (37, 99, 235),
    (15, 118, 110),
    (190, 18, 60),
    (67, 56, 202),
    (180, 83, 9),
]


def _draw_placeholder(path: Path, size: tuple[int, int], label: str, color: tuple[int, int, int]) -> None:
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    short_label = label if size[0] >= 100 else label[-1]
    draw.text((size[0] // 4, size[1] // 2), short_label, fill=(255, 255, 255))
    image.save(path, format="JPEG", quality=15 if max(size) >= 4000 else 85, optimize=True)


def main() -> None:
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for index, size in enumerate(NORMAL_SIZES, start=1):
        path = PHOTOS_DIR / f"portrait_{index:02d}.jpg"
        _draw_placeholder(path, size, f"P{index:02d}", PALETTE[(index - 1) % len(PALETTE)])
        generated.append(path)

    for index, (filename, size) in enumerate(SPECIAL_PHOTOS, start=1):
        path = PHOTOS_DIR / filename
        _draw_placeholder(path, size, f"T{index:02d}", PALETTE[index % len(PALETTE)])
        generated.append(path)

    broken_path = PHOTOS_DIR / "broken.jpg"
    broken_path.write_text(
        "This is deliberately not an image; use it to test unreadable-photo handling.\n",
        encoding="utf-8",
    )
    generated.append(broken_path)

    total_bytes = sum(path.stat().st_size for path in generated)
    print(f"Created {len(generated)} photo test files in {PHOTOS_DIR}")
    print("Dimensions: 20 portrait, 2 tiny, 2 huge compressed, 2 square, 2 landscape")
    print(f"Corrupt image: broken.jpg (text content)")
    print(f"Total folder size: {total_bytes / (1024 * 1024):.2f} MiB")
    if total_bytes >= 5 * 1024 * 1024:
        raise SystemExit("FAIL: generated photos exceed the 5 MiB folder limit")


if __name__ == "__main__":
    main()
