import json
import unittest

from studio.design_tools.config import THEMES_DIR
from studio.design_tools.validate_themes import validate_theme


class ValidateThemeTests(unittest.TestCase):
    def test_all_theme_files_validate(self):
        for filename in ("clean_light.json", "dark_tech.json", "bold_event.json"):
            with self.subTest(theme=filename):
                self.assertEqual(validate_theme(THEMES_DIR / filename), [])

    def test_role_styles_are_distinct_in_grayscale(self):
        for filename in ("clean_light.json", "dark_tech.json", "bold_event.json"):
            with self.subTest(theme=filename):
                with (THEMES_DIR / filename).open(encoding="utf-8") as theme_file:
                    theme = json.load(theme_file)
                styles = theme["role_style"].values()
                self.assertEqual(len({style["badge_shape"] for style in styles}), 3)
                self.assertEqual(len({style["badge_border"] for style in styles}), 3)
                self.assertEqual(len({style["label"] for style in styles}), 3)


if __name__ == "__main__":
    unittest.main()
