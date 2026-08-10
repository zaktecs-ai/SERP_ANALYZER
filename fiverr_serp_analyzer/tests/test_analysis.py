"""Unit tests for analysis modules."""

import os
import sys
import unittest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.keywords import classify_intent, calculate_keyword_relevance, calculate_demand_signal
from analysis.competition import analyze_competition, analyze_serp_concentration
from analysis.scoring import compute_opportunity_score, compute_gig_scores
from analysis.clustering import cluster_keywords, name_clusters
from analysis.gap_analysis import (
    analyze_title_terms,
    identify_underserved_services,
    per_keyword_competitor_extremes,
    find_opportunity_gaps,
)


class TestClassifyIntent(unittest.TestCase):
    """Test intent classification."""

    def test_transactional(self):
        result = classify_intent("buy web scraping service")
        self.assertIn("transactional", result["primary_intent"])

    def test_service_specific(self):
        result = classify_intent("custom python web scraper")
        self.assertIn("service_specific", result["primary_intent"])

    def test_informational(self):
        result = classify_intent("how to scrape website")
        self.assertIn("informational", result["primary_intent"])

    def test_numeric_score_range(self):
        result = classify_intent("scrape data from website")
        self.assertGreaterEqual(result["intent_numeric"], 0)
        self.assertLessEqual(result["intent_numeric"], 100)

    def test_ambiguous(self):
        result = classify_intent("website")
        self.assertEqual(result["primary_intent"], "ambiguous")


class TestCalculateKeywordRelevance(unittest.TestCase):
    """Test keyword relevance calculation."""

    def setUp(self):
        self.gigs = [
            {"title_normalized": "I will scrape data from website to excel"},
            {"title_normalized": "I will extract data from any website"},
            {"title_normalized": "I will build python web scraper"},
        ]

    def test_exact_match_pct(self):
        result = calculate_keyword_relevance("scrape data", self.gigs)
        self.assertGreaterEqual(result["exact_title_match_pct"], 0)
        self.assertLessEqual(result["exact_title_match_pct"], 100)

    def test_empty_gigs(self):
        result = calculate_keyword_relevance("scrape data", [])
        self.assertEqual(result["relevance_score"], 0.0)

    def test_relevance_is_number(self):
        result = calculate_keyword_relevance("web scraping", self.gigs)
        self.assertIsInstance(result["relevance_score"], float)


class TestCalculateDemandSignal(unittest.TestCase):
    """Test demand signal calculation."""

    def test_very_low(self):
        result = calculate_demand_signal(50)
        self.assertEqual(result["demand_signal"], "very_low")
        self.assertEqual(result["demand_score"], 10.0)

    def test_high(self):
        result = calculate_demand_signal(5000)
        self.assertEqual(result["demand_signal"], "high")
        self.assertEqual(result["demand_score"], 75.0)

    def test_none(self):
        result = calculate_demand_signal(None)
        self.assertEqual(result["demand_signal"], "unknown")
        self.assertEqual(result["demand_score"], 50.0)


class TestAnalyzeCompetition(unittest.TestCase):
    """Test competition analysis."""

    def setUp(self):
        self.gigs = [
            {"review_count_cleaned": "1200", "seller_rating_normalized": "4.9",
             "seller_level_normalized": "Level 2 Seller",
             "starting_price_normalized": "15", "title_normalized": "scrape data"},
            {"review_count_cleaned": "450", "seller_rating_normalized": "4.8",
             "seller_level_normalized": "Level 1 Seller",
             "starting_price_normalized": "25", "title_normalized": "extract data"},
            {"review_count_cleaned": "3400", "seller_rating_normalized": "5.0",
             "seller_level_normalized": "Top Rated Seller",
             "starting_price_normalized": "50", "title_normalized": "python scraper"},
        ]

    def test_median_reviews(self):
        result = analyze_competition(self.gigs)
        self.assertEqual(result["median_reviews"], 1200)

    def test_median_rating(self):
        result = analyze_competition(self.gigs)
        self.assertEqual(result["median_rating"], 4.9)

    def test_competition_score_range(self):
        result = analyze_competition(self.gigs)
        self.assertGreaterEqual(result["competition_score"], 0)
        self.assertLessEqual(result["competition_score"], 100)

    def test_empty(self):
        result = analyze_competition([])
        self.assertEqual(result["competition_score"], 50.0)


class TestAnalyzeSerpConcentration(unittest.TestCase):
    """Test SERP concentration analysis."""

    def setUp(self):
        self.gigs = [
            {"review_count_cleaned": "5000"},
            {"review_count_cleaned": "100"},
            {"review_count_cleaned": "50"},
            {"review_count_cleaned": "30"},
            {"review_count_cleaned": "20"},
        ]

    def test_top5_share(self):
        result = analyze_serp_concentration(self.gigs)
        self.assertIsNotNone(result["top5_review_share"])
        self.assertGreaterEqual(result["top5_review_share"], 0)
        self.assertLessEqual(result["top5_review_share"], 100)

    def test_empty(self):
        result = analyze_serp_concentration([])
        self.assertEqual(result["serp_strength_score"], 50.0)


class TestComputeOpportunityScore(unittest.TestCase):
    """Test opportunity scoring."""

    def test_basic(self):
        result = compute_opportunity_score(
            demand_score=75,
            intent_score=80,
            relevance_score=60,
            competition_score=40,
            serp_strength_score=50,
        )
        self.assertIsInstance(result["opportunity_score"], float)
        self.assertGreaterEqual(result["opportunity_score"], 0)
        self.assertLessEqual(result["opportunity_score"], 100)

    def test_high_competition_lowers_score(self):
        low_comp = compute_opportunity_score(75, 80, 60, 20, 50)
        high_comp = compute_opportunity_score(75, 80, 60, 80, 50)
        self.assertGreater(low_comp["opportunity_score"], high_comp["opportunity_score"])

    def test_custom_weights(self):
        result = compute_opportunity_score(
            75, 80, 60, 40, 50,
            weights={"demand": 0.5, "intent": 0.1, "relevance": 0.1,
                     "competition": 0.2, "serp_weakness": 0.1},
        )
        self.assertIsNotNone(result["opportunity_score"])


class TestComputeGigScores(unittest.TestCase):
    """Test per-gig scoring."""

    def test_basic(self):
        gig = {
            "title_normalized": "I will scrape data from website",
            "review_count_cleaned": "1200",
            "seller_rating_normalized": "4.9",
            "starting_price_normalized": "15",
            "serp_position": 1,
        }
        result = compute_gig_scores(gig, "scrape data")
        self.assertIn("title_optimization_score", result)
        self.assertIn("seller_strength_score", result)
        self.assertIn("review_strength_score", result)
        self.assertIn("rating_strength_score", result)

    def test_missing_data(self):
        gig = {}
        result = compute_gig_scores(gig, "scrape")
        self.assertIsNotNone(result["seller_strength_score"])


class TestClustering(unittest.TestCase):
    """Test keyword clustering."""

    def test_groups_similar(self):
        kws = [
            "scrape data from website",
            "scrape website data",
            "extract data from website",
            "python web scraping",
            "custom python scraper",
        ]
        clusters = cluster_keywords(kws)
        self.assertGreaterEqual(len(clusters), 2)

    def test_empty(self):
        clusters = cluster_keywords([])
        self.assertEqual(clusters, {})

    def test_name_clusters(self):
        kws = ["scrape data", "data extraction"]
        clusters = cluster_keywords(kws)
        named = name_clusters(clusters)
        for cid, cdata in named.items():
            self.assertIn("name", cdata)
            self.assertIn("keywords", cdata)
            self.assertIn("size", cdata)


class TestGapAnalysis(unittest.TestCase):
    """Test gap analysis functions."""

    def test_title_terms(self):
        gigs = [
            {"title_normalized": "I will scrape data from website"},
            {"title_normalized": "I will scrape data from any website"},
            {"title_normalized": "I will extract data from website"},
        ]
        result = analyze_title_terms(gigs)
        self.assertIn("frequent_terms", result)
        self.assertIn("rare_terms", result)

    def test_underserved(self):
        gigs = [
            {"title_normalized": "I will scrape data from website",
             "review_count_cleaned": "10", "serp_position": 1},
            {"title_normalized": "I will extract data",
             "review_count_cleaned": "20", "serp_position": 2},
        ]
        result = identify_underserved_services("scrape data", gigs)
        self.assertGreaterEqual(len(result), 1)

    def test_competitor_extremes(self):
        gigs = [
            {"title_normalized": "scraper a", "review_count_cleaned": "100",
             "seller_rating_normalized": "4.9", "serp_position": 1},
            {"title_normalized": "scraper b", "review_count_cleaned": "5",
             "seller_rating_normalized": "4.0", "serp_position": 2},
        ]
        result = per_keyword_competitor_extremes(gigs)
        self.assertIn("strongest_competitor", result)
        self.assertIn("weakest_competitor", result)

    def test_opportunity_gaps(self):
        analyses = [
            {"keyword": "kw1", "intent_score": 80, "competition_score": 20,
             "opportunity_score": 85, "serp_strength_score": 30},
            {"keyword": "kw2", "intent_score": 30, "competition_score": 80,
             "opportunity_score": 40, "serp_strength_score": 70},
        ]
        gaps = find_opportunity_gaps(analyses)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["keyword"], "kw1")


if __name__ == "__main__":
    unittest.main()