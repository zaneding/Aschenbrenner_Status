import json
import tempfile
import unittest
from pathlib import Path

from tracker.notion_update import (
    build_notion_child_page_title,
    build_notion_markdown,
    check_new_filing,
    mark_notified,
)


SNAPSHOT = {
    "manager": "Situational Awareness LP",
    "cik": "0002045724",
    "fetched_at": "2026-05-05T16:34:59+00:00",
    "latest_filing": {
        "accession": "0002045724-26-000002",
        "filing_date": "2026-02-11",
        "report_date": "2025-12-31",
        "form": "13F-HR",
        "sec_url": "https://www.sec.gov/Archives/edgar/data/2045724/000204572426000002/",
    },
    "summary": {
        "total_value_usd": 5516758345,
        "position_count": 29,
        "top_5_weight": 0.6003534925545121,
        "option_weight": 0.290589304397019,
        "holdings": [
            {
                "issuer": "BLOOM ENERGY CORP",
                "ticker": "BE",
                "cusip": "093712107",
                "value_usd": 875505552,
                "weight": 0.15869927541660336,
                "shares": 10076022,
                "put_call": "",
                "sector": "Energy",
            },
            {
                "issuer": "COREWEAVE INC",
                "ticker": "CRWV",
                "cusip": "21873S108",
                "value_usd": 774426345,
                "weight": 0.14037706503890737,
                "shares": 10814500,
                "put_call": "Call",
                "sector": "AI Infrastructure",
            }
        ],
    },
    "changes": [
        {
            "issuer": "COREWEAVE INC",
            "cusip": "21873S108",
            "position_type": "Call",
            "status": "new",
            "value_delta_usd": 774426345,
            "share_delta": 10814500,
        }
    ],
}


class NotionUpdateTests(unittest.TestCase):
    def test_check_new_filing_writes_markdown_when_accession_is_unseen(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)

            result = check_new_filing(SNAPSHOT, data_dir)

            self.assertTrue(result["has_new_filing"])
            self.assertTrue(Path(result["markdown_path"]).exists())
            self.assertEqual(result["page_title"], "13F 2025-12-31 - 0002045724-26-000002")
            self.assertIn("0002045724-26-000002", Path(result["markdown_path"]).read_text())

    def test_check_new_filing_skips_seen_accession(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            mark_notified(data_dir, "0002045724-26-000002")

            result = check_new_filing(SNAPSHOT, data_dir)

            self.assertFalse(result["has_new_filing"])
            self.assertIsNone(result["markdown_path"])

    def test_markdown_contains_summary_and_changes(self):
        markdown = build_notion_markdown(SNAPSHOT)

        self.assertIn("13F Dashboard - 2025-12-31", markdown)
        self.assertIn("Bloom Energy Corp", markdown)
        self.assertIn("Coreweave Inc", markdown)
        self.assertIn("Portfolio heat map", markdown)
        self.assertIn("Sector allocation", markdown)
        self.assertIn("{color=\"green\"}", markdown)
        self.assertIn("https://www.sec.gov/Archives", markdown)

    def test_child_page_title_uses_report_date_and_accession(self):
        title = build_notion_child_page_title(SNAPSHOT)

        self.assertEqual(title, "13F 2025-12-31 - 0002045724-26-000002")

    def test_mark_notified_persists_accession(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)

            mark_notified(data_dir, "abc")
            state = json.loads((data_dir / "notion_state.json").read_text())

            self.assertEqual(state["last_notified_accession"], "abc")


if __name__ == "__main__":
    unittest.main()
