"""CSV export for the Fiverr SERP Analyzer."""

import csv
import os


def export_keyword_summary(keyword_analyses: list, output_path: str = "keyword_summary.csv"):
    """Export keyword summary to CSV."""
    if not keyword_analyses:
        print("No keyword data to export.")
        return

    fieldnames = [
        "keyword", "primary_intent", "intent_score", "demand_signal",
        "total_results", "gig_count", "median_reviews", "median_rating",
        "competition_score", "serp_strength_score", "relevance_score",
        "opportunity_score", "cluster_name", "status",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for analysis in keyword_analyses:
            writer.writerow(analysis)

    print(f"Keyword summary CSV saved to: {output_path}")


def export_top20_gigs(all_gigs: list, output_path: str = "top20_gigs.csv"):
    """Export top 20 gigs to CSV."""
    if not all_gigs:
        print("No gig data to export.")
        return

    fieldnames = [
        "keyword", "serp_position", "title_normalized", "url_normalized",
        "seller_name_normalized", "seller_level_normalized",
        "seller_rating_normalized", "review_count_cleaned",
        "starting_price_normalized", "delivery_time_normalized",
        "category_normalized",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for gig in all_gigs:
            writer.writerow(gig)

    print(f"Top 20 gigs CSV saved to: {output_path}")


def export_competitor_analysis(keyword_analyses: list,
                               output_path: str = "competitor_analysis.csv"):
    """Export competitor analysis to CSV."""
    if not keyword_analyses:
        print("No competitor data to export.")
        return

    fieldnames = [
        "keyword", "serp_position", "title", "title_optimization_score",
        "keyword_relevance_score", "seller_strength_score",
        "review_strength_score", "rating_strength_score",
        "price_positioning_score",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for analysis in keyword_analyses:
            for gs in analysis.get("gig_scores", []):
                row = {
                    "keyword": analysis.get("keyword"),
                    "serp_position": gs.get("serp_position"),
                    "title": gs.get("title", "")[:100],
                    "title_optimization_score": gs.get("title_optimization_score"),
                    "keyword_relevance_score": gs.get("keyword_relevance_score"),
                    "seller_strength_score": gs.get("seller_strength_score"),
                    "review_strength_score": gs.get("review_strength_score"),
                    "rating_strength_score": gs.get("rating_strength_score"),
                    "price_positioning_score": gs.get("price_positioning_score"),
                }
                writer.writerow(row)

    print(f"Competitor analysis CSV saved to: {output_path}")


def export_keyword_opportunities(keyword_analyses: list,
                                 output_path: str = "keyword_opportunities.csv"):
    """Export keyword opportunities (ranked) to CSV."""
    if not keyword_analyses:
        print("No opportunity data to export.")
        return

    fieldnames = [
        "rank", "keyword", "opportunity_score", "demand_score",
        "intent_score", "relevance_score", "competition_score",
        "serp_weakness_score", "primary_intent", "demand_signal",
    ]

    ranked = sorted(
        keyword_analyses,
        key=lambda x: x.get("opportunity_score", 0),
        reverse=True,
    )

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for i, analysis in enumerate(ranked, 1):
            row = {**analysis, "rank": i}
            writer.writerow(row)

    print(f"Keyword opportunities CSV saved to: {output_path}")