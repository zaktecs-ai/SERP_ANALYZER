"""Unit tests for challenge detection heuristics."""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.challenge import ChallengeDetector


class TestChallengeDetector(unittest.TestCase):
    """Test challenge detection."""

    def setUp(self):
        self.detector = ChallengeDetector(max_challenges=3)

    def _make_driver(self, title="scrape data | Search | Fiverr",
                     source="<html><body><div class='gig-card-layout'>test</div></body></html>"):
        driver = MagicMock()
        driver.title = title
        driver.page_source = source
        driver.find_element.side_effect = Exception("not found")
        return driver

    def test_normal_page_not_challenge(self):
        driver = self._make_driver()
        self.assertFalse(self.detector.detect(driver))

    def test_challenge_title_detected(self):
        driver = self._make_driver(title="Verify you are human | Fiverr")
        self.assertTrue(self.detector.detect(driver))

    def test_captcha_title_detected(self):
        driver = self._make_driver(title="Security Check - Captcha")
        self.assertTrue(self.detector.detect(driver))

    def test_blocked_title_detected(self):
        driver = self._make_driver(title="Access Denied")
        self.assertTrue(self.detector.detect(driver))

    def test_challenge_dom_detected(self):
        driver = self._make_driver()
        # Make captcha element found and displayed
        def find_element(by, selector):
            if selector == "div#captcha":
                el = MagicMock()
                el.is_displayed.return_value = True
                return el
            raise Exception("not found")
        driver.find_element.side_effect = find_element
        self.assertTrue(self.detector.detect(driver))

    def test_challenge_body_text_detected(self):
        driver = self._make_driver(
            source="<html><body><p>We've detected unusual traffic from your computer</p></body></html>"
        )
        self.assertTrue(self.detector.detect(driver))

    def test_max_challenges(self):
        detector = ChallengeDetector(max_challenges=1)
        detector.challenge_count = 1
        driver = self._make_driver()
        result = detector.handle_challenge(driver, "keyword", "http://test")
        self.assertFalse(result)  # Should return False when max exceeded

    def test_reset(self):
        self.detector.challenge_count = 2
        self.detector.reset()
        self.assertEqual(self.detector.challenge_count, 0)


if __name__ == "__main__":
    unittest.main()