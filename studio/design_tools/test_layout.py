import json
import unittest
from pathlib import Path

from studio.design_tools.config import LAYOUTS_DIR
from studio.design_tools.layout import prepare_layout


class PrepareLayoutTests(unittest.TestCase):
    def test_blank_rows_are_removed_and_later_rows_compact_in_their_group(self):
        layout = {
            "elements": [
                {"type": "text", "field": "organization", "y": 10, "collapse_group": "details"},
                {
                    "type": "text",
                    "field": "team",
                    "y": 15,
                    "collapse_if_empty": True,
                    "collapse_group": "details",
                    "collapse_height": 4,
                },
                {
                    "type": "text",
                    "field": "id_number",
                    "y": 20,
                    "collapse_if_empty": True,
                    "collapse_group": "details",
                    "collapse_height": 3,
                },
                {"type": "text", "field": "role", "y": 25, "collapse_group": "details"},
                {"type": "qr", "field": "qr_data", "y": 30},
            ]
        }

        result = prepare_layout(layout, {"team": "  ", "id_number": None})

        self.assertEqual(
            [(element["field"], element.get("y")) for element in result["elements"]],
            [("organization", 10), ("role", 18), ("qr_data", 30)],
        )
        self.assertEqual(layout["elements"][3]["y"], 25)

    def test_populated_optional_rows_remain_in_place(self):
        layout = {
            "elements": [
                {
                    "type": "text",
                    "field": "team",
                    "y": 15,
                    "collapse_if_empty": True,
                    "collapse_group": "details",
                    "collapse_height": 4,
                },
                {"type": "text", "field": "role", "y": 25, "collapse_group": "details"},
            ]
        }

        result = prepare_layout(layout, {"team": "Design"})

        self.assertEqual([element["y"] for element in result["elements"]], [15, 25])

    def test_invalid_collapse_metadata_is_reported(self):
        layout = {
            "elements": [
                {"type": "text", "field": "team", "y": 15, "collapse_if_empty": True}
            ]
        }

        with self.assertRaisesRegex(ValueError, "collapse_group"):
            prepare_layout(layout, {})

    def test_all_templates_remove_missing_optional_fields(self):
        for name in ("classic.json", "modern_split.json", "minimal.json"):
            with self.subTest(layout=name):
                with (LAYOUTS_DIR / name).open(encoding="utf-8") as layout_file:
                    layout = json.load(layout_file)

                result = prepare_layout(layout, {})
                text_fields = [
                    element["field"]
                    for element in result["elements"]
                    if element.get("type") == "text"
                ]

                self.assertNotIn("team", text_fields)
                self.assertNotIn("id_number", text_fields)


if __name__ == "__main__":
    unittest.main()
