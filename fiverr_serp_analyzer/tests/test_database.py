"""Unit tests for database storage and checkpoint functionality."""

import os
import sys
import tempfile
import unittest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabase(unittest.TestCase):
    """Test database storage operations."""

    def setUp(self):
        """Set up a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        from database.storage import StorageManager
        self.storage = StorageManager(self.db_path)

    def tearDown(self):
        """Clean up database."""
        self.storage.close()
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def test_create_run(self):
        """Test creating a collection run."""
        ok = self.storage.create_run("run_test_1", 5)
        self.assertTrue(ok)
        info = self.storage.get_run_info("run_test_1")
        self.assertIsNotNone(info)
        self.assertEqual(info["total_keywords"], 5)

    def test_save_keyword_results(self):
        """Test saving collected results."""
        run_id = "run_test_2"
        self.storage.create_run(run_id, 1)

        result = {
            "keyword": "scrape data from website",
            "url": "https://www.fiverr.com/search/gigs?query=test",
            "total_results_raw": "6,759 results",
            "total_results_parsed": 6759,
            "total_results_state": "extracted",
            "error": None,
            "challenge_paused": False,
            "collection_timestamp": "2026-01-01T00:00:00",
            "gigs": [
                {
                    "serp_position": 1,
                    "collection_timestamp": "2026-01-01T00:00:00",
                    "title_raw": "I will scrape data from website",
                    "title_normalized": "i will scrape data from website",
                    "title_state": "extracted",
                    "title_selector": "a.gig-link h3",
                    "url_raw": "https://www.fiverr.com/gig/123-scrape",
                    "url_normalized": "https://www.fiverr.com/gig/123-scrape",
                    "url_state": "extracted",
                    "url_selector": "a.gig-link",
                    "gig_id_raw": "123",
                    "gig_id_normalized": "123",
                    "gig_id_state": "extracted",
                    "gig_id_selector": "data-gig-id",
                    "seller_name_raw": "TestSeller",
                    "seller_name_normalized": "testseller",
                    "seller_name_state": "extracted",
                    "seller_name_selector": "a.seller-name",
                    "seller_profile_url_raw": "https://www.fiverr.com/testseller",
                    "seller_profile_url_normalized": "https://www.fiverr.com/testseller",
                    "seller_profile_url_state": "extracted",
                    "seller_profile_url_selector": "a.seller-name",
                    "seller_level_raw": "Level 2 Seller",
                    "seller_level_normalized": "level 2 seller",
                    "seller_level_state": "extracted",
                    "seller_level_selector": "span.seller-level",
                    "seller_rating_raw": "4.9",
                    "seller_rating_normalized": "4.9",
                    "seller_rating_state": "extracted",
                    "seller_rating_selector": "span.rating-score",
                    "review_count_raw": "(1.2k)",
                    "review_count_cleaned": "1.2k",
                    "review_count_state": "extracted",
                    "review_count_selector": "span.rating-count",
                    "starting_price_raw": "$15",
                    "starting_price_normalized": "$15",
                    "starting_price_state": "extracted",
                    "starting_price_selector": "span.price",
                    "delivery_time_raw": "3 days",
                    "delivery_time_normalized": "3 days",
                    "delivery_time_state": "extracted",
                    "delivery_time_selector": "span.delivery-time",
                    "badges_raw": ["Top Rated"],
                    "badges_normalized": ["top rated"],
                    "badges_state": "extracted",
                    "badges_selector": "span.badge",
                    "category_raw": None,
                    "category_normalized": None,
                    "category_state": "missing",
                    "category_selector": None,
                    "service_tags_raw": ["web scraping"],
                    "service_tags_normalized": ["web scraping"],
                    "service_tags_state": "extracted",
                    "service_tags_selector": "span.tag",
                    "card_selector_used": "div.gig-card-layout",
                }
            ],
        }

        ok = self.storage.save_keyword_results(run_id, "scrape data from website", result)
        self.assertTrue(ok)

        # Verify keyword was saved
        kw_id = self.storage.get_keyword_id("scrape data from website")
        self.assertIsNotNone(kw_id)

        # Verify gigs were saved
        rows = self.storage.get_all_keyword_gigs(run_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title_normalized"], "i will scrape data from website")

    def test_duplicate_keyword_not_duplicated(self):
        """Test that saving same keyword twice upserts, doesn't duplicate."""
        run_id = "run_test_3"
        self.storage.create_run(run_id, 2)

        result = {
            "keyword": "test keyword",
            "url": "https://test",
            "total_results_raw": None,
            "total_results_parsed": None,
            "total_results_state": "missing",
            "error": None,
            "challenge_paused": False,
            "collection_timestamp": "2026-01-01T00:00:00",
            "gigs": [],
        }

        ok1 = self.storage.save_keyword_results(run_id, "test keyword", result)
        ok2 = self.storage.save_keyword_results(run_id, "test keyword", result)
        self.assertTrue(ok1)
        self.assertTrue(ok2)

        kws = self.storage.get_all_keywords(run_id)
        self.assertEqual(len(kws), 1)

    def test_error_logging(self):
        """Test error logging."""
        run_id = "run_test_4"
        self.storage.create_run(run_id, 1)
        self.storage.log_error(run_id, "keyword1", "timeout", "Page timed out")
        errors = self.storage.get_errors(run_id)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["error_type"], "timeout")


class TestCheckpoint(unittest.TestCase):
    """Test checkpoint manager."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cp_path = os.path.join(self.temp_dir, "checkpoint.json")
        from utils.checkpoint import CheckpointManager
        self.cp = CheckpointManager(self.cp_path)

    def test_mark_completed(self):
        self.cp.mark_completed("test keyword", 20)
        self.assertTrue(self.cp.is_completed("test keyword"))

    def test_case_insensitive_completion(self):
        self.cp.mark_completed("Scrape Data", 20)
        self.assertTrue(self.cp.is_completed("scrape data"))

    def test_failed_keyword(self):
        self.cp.mark_failed("bad keyword", "timeout")
        self.assertTrue(self.cp.is_failed("bad keyword"))

    def test_get_pending(self):
        self.cp.mark_completed("done kw")
        all_kws = ["done kw", "new kw", "failed kw"]
        self.cp.mark_failed("failed kw", "error")

        # Without resume: skip completed, skip failed
        pending = self.cp.get_pending_keywords(all_kws)
        self.assertEqual(pending, ["new kw"])

        # With resume: include failed
        pending = self.cp.get_pending_keywords(all_kws, resume=True)
        self.assertEqual(pending, ["new kw", "failed kw"])

        # With force: include everything
        pending = self.cp.get_pending_keywords(all_kws, force=True)
        self.assertEqual(pending, all_kws)

    def test_mark_failed_removes_on_complete(self):
        self.cp.mark_failed("kw", "error")
        self.cp.mark_completed("kw", 10)
        self.assertFalse(self.cp.is_failed("kw"))
        self.assertTrue(self.cp.is_completed("kw"))


if __name__ == "__main__":
    unittest.main()