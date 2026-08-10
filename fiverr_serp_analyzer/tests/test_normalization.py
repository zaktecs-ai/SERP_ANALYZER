"""Unit tests for normalization and parsing utilities."""

import os
import sys
import unittest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.normalization import (
    normalize_text,
    normalize_url,
    parse_number,
    parse_price,
    parse_rating,
    parse_review_count,
    normalize_title,
    tokenize,
    keyword_token_match,
)


class TestParseNumber(unittest.TestCase):
    """Test number parsing utilities."""

    def test_plain_number(self):
        self.assertEqual(parse_number("245"), 245.0)

    def test_thousands_separator(self):
        self.assertEqual(parse_number("10,000"), 10000.0)

    def test_k_suffix(self):
        self.assertEqual(parse_number("1.2k"), 1200.0)

    def test_k_suffix_uppercase(self):
        self.assertEqual(parse_number("2K"), 2000.0)

    def test_m_suffix(self):
        self.assertEqual(parse_number("1.5m"), 1500000.0)

    def test_none_input(self):
        self.assertIsNone(parse_number(None))

    def test_empty_string(self):
        self.assertIsNone(parse_number(""))

    def test_invalid_string(self):
        self.assertIsNone(parse_number("abc"))

    def test_decimal(self):
        self.assertEqual(parse_number("4.9"), 4.9)


class TestParsePrice(unittest.TestCase):
    """Test price parsing."""

    def test_dollar(self):
        self.assertEqual(parse_price("$20"), 20.0)

    def test_dollar_decimal(self):
        self.assertEqual(parse_price("$5.99"), 5.99)

    def test_euro(self):
        self.assertEqual(parse_price("€50"), 50.0)

    def test_thousands(self):
        self.assertEqual(parse_price("$1,000"), 1000.0)

    def test_none(self):
        self.assertIsNone(parse_price(None))

    def test_empty(self):
        self.assertIsNone(parse_price(""))


class TestParseRating(unittest.TestCase):
    """Test rating parsing."""

    def test_valid_rating(self):
        self.assertEqual(parse_rating("4.9"), 4.9)

    def test_five(self):
        self.assertEqual(parse_rating("5.0"), 5.0)

    def test_zero(self):
        self.assertEqual(parse_rating("0"), 0.0)

    def test_invalid_higher_than_five(self):
        self.assertIsNone(parse_rating("6.0"))

    def test_invalid_text(self):
        self.assertIsNone(parse_rating("excellent"))


class TestParseReviewCount(unittest.TestCase):
    """Test review count parsing."""

    def test_plain(self):
        self.assertEqual(parse_review_count("245"), 245)

    def test_k(self):
        self.assertEqual(parse_review_count("1.2k"), 1200)

    def test_thousands(self):
        self.assertEqual(parse_review_count("10,000"), 10000)

    def test_missing(self):
        self.assertIsNone(parse_review_count(None))


class TestNormalizeText(unittest.TestCase):
    """Test text normalization."""

    def test_whitespace(self):
        self.assertEqual(normalize_text("  hello   world  "), "hello world")

    def test_unicode_nfc(self):
        self.assertEqual(normalize_text("caf\u00e9"), "caf\u00e9")

    def test_none(self):
        self.assertEqual(normalize_text(None), "")


class TestNormalizeUrl(unittest.TestCase):
    """Test URL normalization."""

    def test_tracking_params_stripped(self):
        url = "https://www.fiverr.com/gig/123?utm_source=google&ref=test"
        result = normalize_url(url)
        self.assertNotIn("utm_source", result)
        self.assertNotIn("ref=", result)

    def test_fragment_stripped(self):
        url = "https://www.fiverr.com/gig/123#section"
        result = normalize_url(url)
        self.assertNotIn("#section", result)

    def test_lowercase_host(self):
        url = "HTTPS://WWW.Fiverr.com/Gig/123"
        result = normalize_url(url)
        self.assertIn("www.fiverr.com/gig/123", result)

    def test_trailing_slash(self):
        url = "https://www.fiverr.com/gig/123/"
        result = normalize_url(url)
        self.assertFalse(result.endswith("/"))


class TestNormalizeTitle(unittest.TestCase):
    """Test title normalization."""

    def test_lowercase(self):
        self.assertEqual(normalize_title("SCRAPE DATA"), "scrape data")

    def test_whitespace(self):
        self.assertEqual(normalize_title("  Scrape   Data  "), "scrape data")


class TestTokenize(unittest.TestCase):
    """Test tokenization."""

    def test_basic(self):
        result = tokenize("web scraping service")
        self.assertEqual(result, {"web", "scraping", "service"})

    def test_empty(self):
        self.assertEqual(tokenize(""), set())

    def test_none(self):
        self.assertEqual(tokenize(None), set())

    def test_punctuation(self):
        result = tokenize("web-scraping, python!")
        self.assertIn("web", result)
        self.assertIn("scraping", result)


class TestKeywordTokenMatch(unittest.TestCase):
    """Test keyword matching logic."""

    def test_exact_match(self):
        result = keyword_token_match("scrape data", "I will scrape data from website")
        self.assertTrue(result["exact_match"])
        self.assertTrue(result["phrase_match"])

    def test_no_match(self):
        result = keyword_token_match("ecommerce scraping", "I will design a logo")
        self.assertFalse(result["exact_match"])
        self.assertEqual(result["token_matches"], 0)

    def test_partial_match(self):
        result = keyword_token_match("python web scraping", "I will do web scraping")
        self.assertFalse(result["exact_match"])
        self.assertEqual(result["token_matches"], 2)  # web, scraping
        self.assertGreater(result["token_match_ratio"], 0)

    def test_keyword_position(self):
        result = keyword_token_match("scrape", "I will scrape data")
        self.assertEqual(result["keyword_position"], 2)

    def test_keyword_position_not_found(self):
        result = keyword_token_match("scrape", "I will extract data")
        self.assertIsNone(result["keyword_position"])


if __name__ == "__main__":
    unittest.main()