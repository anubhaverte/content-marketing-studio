"""Render all layout/theme combinations for normal, long-name, and no-photo people."""

import io
import sys
import warnings
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from studio.design_tools.config import SAMPLE_DATA_DIR
from studio.design_tools.render_card import load_attendees, load_layout_theme, render_png

LAYOUT_NAMES = ("classic", "modern_split", "minimal")
THEME_NAMES = ("clean_light", "dark_tech", "bold_event")
CARD_WIDTH = 240
CELL_LABEL_HEIGHT = 34
TITLE_HEIGHT = 34
PADDING = 18
VALID_ROLES = {"participant", "organizer", "mentor"}


def _select_people() -> list[tuple[str, dict[str, str]]]:
    attendees = load_attendees()
    normal = next(
        attendee
        for attendee in attendees
        if attendee["full_name"] == "Aarav Sharma"
        and attendee["photo"]
        and attendee["role"].lower() in VALID_ROLES
    )
    long_name = next(
        attendee
        for attendee in attendees
        if len(attendee["full_name"]) >= 45
        and attendee["photo"]
        and attendee["role"].lower() in VALID_ROLES
    )
    no_photo = next(
        attendee
        for attendee in attendees
        if attendee["full_name"] == "Aarav Sharma"
        and not attendee["photo"]
        and attendee["role"].lower() in VALID_ROLES
    )
    return [("NORMAL", normal), ("LONG NAME", long_name), ("NO PHOTO", no_photo)]


def main() -> None:
    people = _select_people()
    columns = len(people)
    rows = len(LAYOUT_NAMES) * len(THEME_NAMES)
    cell_width = CARD_WIDTH + PADDING * 2
    cell_height = round(CARD_WIDTH * 92 / 60) + CELL_LABEL_HEIGHT + PADDING
    sheet = Image.new(
        "RGB",
        (
            columns * cell_width + PADDING,
            TITLE_HEIGHT + rows * cell_height + PADDING,
        ),
        (238, 242, 247),
    )
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.load_default()
    draw.text(
        (PADDING, 8),
        "TEMPORARY STAND-IN — NOT THE PRODUCTION RENDERER",
        fill=(22, 32, 51),
        font=label_font,
    )

    for row_index, (layout_name, theme_name) in enumerate(
        (pair for layout_name in LAYOUT_NAMES for pair in ((layout_name, name) for name in THEME_NAMES))
    ):
        layout, theme = load_layout_theme(layout_name, theme_name)
        for column_index, (person_label, attendee) in enumerate(people):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                png = render_png(layout, theme, attendee, output_width=CARD_WIDTH)
            card = Image.open(io.BytesIO(png)).convert("RGB")
            x = PADDING + column_index * cell_width
            y = TITLE_HEIGHT + PADDING + row_index * cell_height
            draw.text(
                (x, y),
                f"{layout_name} / {theme_name} / {person_label}",
                fill=(22, 32, 51),
                font=label_font,
            )
            sheet.paste(card, (x, y + CELL_LABEL_HEIGHT))
            card.close()

    output = SAMPLE_DATA_DIR / "contact_sheet.png"
    sheet.save(output, format="PNG", optimize=True)
    print(
        f"Created {output}: {rows} layout/theme combinations x "
        f"{columns} attendee cases ({rows * columns} cards)"
    )


if __name__ == "__main__":
    main()
