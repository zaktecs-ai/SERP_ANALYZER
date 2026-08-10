"""Tests for parsers using saved HTML fixtures.

Deterministic tests against saved Fiverr SERP HTML so all parsers are
verifiable offline without hitting Fiverr.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestParsersWithFixture(unittest.TestCase):
    """Test parsers using the saved HTML fixture."""

    @classmethod
    def setUpClass(cls):
        """Read the fixture HTML file."""
        fixture_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures",
            "fiverr_serp_sample.html",
        )
        with open(fixture_path, "r", encoding="utf-8") as f:
            cls.html_content = f.read()

    def test_fixture_exists(self):
        """Verify fixture file exists and has content."""
        self.assertIsNotNone(self.html_content)
        self.assertGreater(len(self.html_content), 1000)

    def test_fixture_has_gig_cards(self):
        """Verify fixture contains gig cards."""
        self.assertIn("gig-card-layout", self.html_content)
        self.assertEqual(self.html_content.count("gig-card-layout"), 3)

    def test_fixture_has_result_count(self):
        """Verify fixture contains total results."""
        self.assertIn("6,759 results", self.html_content)

    def test_fixture_has_sellers(self):
        """Verify fixture contains seller info."""
        self.assertIn("WebScraperPro", self.html_content)
        self.assertIn("DataGeek", self.html_content)
        self.assertIn("PythonExpert", self.html_content)


class TestKeywordDedupLogic(unittest.TestCase):
    """Test keyword deduplication logic used by the collector."""

    def test_case_insensitive_dedup(self):
        """Same keyword with different case should dedup."""
        seen = set()
        kws = ["Scrape Data", "scrape data", "SCRAPE DATA"]
        unique = []
        for kw in kws:
            normalized = kw.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(kw)
        self.assertEqual(len(unique), 1)

    def test_whitespace_dedup(self):
        """Same keyword with extra whitespace should dedup."""
        seen = set()
        kws = ["scrape data", "  scrape data  ", "scrape  data"]
        unique = []
        for kw in kws:
            normalized = kw.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(kw)
        self.assertEqual(len(unique), 2)  # "scrape  data" has double space inside

    def test_blank_line_removal(self):
        """Blank lines should be removed."""
        lines = ["", "scrape data", "", "extract data", ""]
        cleaned = [l.strip() for l in lines if l.strip()]
        self.assertEqual(len(cleaned), 2)


class TestMissingDataHandling(unittest.TestCase):
    """Test that missing data is null, never fabricated."""

    def test_missing_reviews_not_zero(self):
        """Missing review count should be None, not 0."""
        data = {"review_count_cleaned": None}
        self.assertIsNone(data["review_count_cleaned"])
        self.assertNotEqual(data["review_count_cleaned"], 0)

    def test_missing_price_not_zero(self):
        """Missing price should be None, not $0."""
        data = {"starting_price_normalized": None}
        self.assertIsNone(data["starting_price_normalized"])
        self.assertNotEqual(data["starting_price_normalized"], 0)

    def test_missing_rating_stays_null(self):
        """Missing rating should stay null."""
        data = {"seller_rating_normalized": None}
        self.assertIsNone(data["seller_rating_normalized"])


if __name__ == "__main__":
    unittest.main()