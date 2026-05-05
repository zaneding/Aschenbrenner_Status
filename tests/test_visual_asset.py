import tempfile
import unittest
from pathlib import Path

from tests.test_notion_update import SNAPSHOT
from tracker.visual_asset import build_svg_dashboard, write_svg_dashboard


class VisualAssetTests(unittest.TestCase):
    def test_build_svg_dashboard_contains_colored_sections(self):
        svg = build_svg_dashboard(SNAPSHOT)

        self.assertIn("<svg", svg)
        self.assertIn("#0f7a56", svg)
        self.assertIn("Bloom Energy Corp", svg)
        self.assertIn("Sector allocation", svg)

    def test_write_svg_dashboard_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = write_svg_dashboard(SNAPSHOT, Path(tmp))

            self.assertTrue(output.exists())
            self.assertEqual(output.suffix, ".svg")
            self.assertIn("0002045724-26-000002", output.name)


if __name__ == "__main__":
    unittest.main()
