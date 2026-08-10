#!/usr/bin/env python3
"""Fiverr SERP Analyzer — main entry point.

Collects and analyzes Fiverr SERP data for web-scraping-related keywords.

Usage:
    python main.py --input keywords.csv
    python main.py --input keywords.csv --top 20
    python main.py --input keywords.csv --resume
    python main.py --input keywords.csv --force
    python main.py --keyword "scrape ecommerce website"
    python main.py --input keywords.csv --max-keywords 25
"""

import argparse
import csv
import os
import signal
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml

from analysis.clustering import cluster_keywords, name_clusters
from analysis.competition import analyze_competition, analyze_serp_concentration
from analysis.gap_analysis import (
    analyze_title_terms,
    find_opportunity_gaps,
    identify_underserved_services,
    per_keyword_competitor_extremes,
)
from analysis.keywords import (
    calculate_demand_signal,
    calculate_keyword_relevance,
    classify_intent,
)
from analysis.scoring import compute_gig_scores, compute_opportunity_score
from database.storage import StorageManager
from reports.competitive_report import generate_competitive_report
from reports.csv_export import (
    export_competitor_analysis,
    export_keyword_opportunities,
    export_keyword_summary,
    export_top20_gigs,
)
from reports.excel import generate_excel
from reports.json_export import export_results_json
from scraper.browser import BrowserManager
from scraper.fiverr import FiverrCollector
from utils.checkpoint import CheckpointManager
from utils.logging import log_error, log_collection, setup_logging


def load_config(config_path: str = "config.yaml") -> dict:
    """Load YAML config file."""
    if not os.path.exists(config_path):
        print(f"ERROR: Config file '{config_path}' not found.")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config or {}


def load_keywords(input_path: str) -> list:
    """Load and clean keywords from a CSV file.

    Handles: duplicate removal (case/whitespace-insensitive), blank-line
    removal, and returns a clean deduplicated list.
    """
    if not os.path.exists(input_path):
        print(f"ERROR: Input file '{input_path}' not found.")
        sys.exit(1)

    keywords = []
    seen = set()

    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Check header includes 'keyword'
        if "keyword" not in (reader.fieldnames or []):
            # Try plain line-by-line parsing
            f.seek(0)
            for line in f:
                kw = line.strip()
                if kw and kw.lower() != "keyword":
                    normalized = kw.lower().strip()
                    if normalized not in seen:
                        seen.add(normalized)
                        keywords.append(kw)
        else:
            for row in reader:
                kw = (row.get("keyword") or "").strip()
                if kw:
                    normalized = kw.lower().strip()
                    if normalized not in seen:
                        seen.add(normalized)
                        keywords.append(kw)

    if not keywords:
        print("ERROR: No keywords found in input file.")
        sys.exit(1)

    return keywords


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"


def main():
    parser = argparse.ArgumentParser(
        description="Fiverr SERP Analyzer — keyword & competition analysis"
    )
    parser.add_argument("--input", type=str, default="keywords.csv",
                        help="Path to keywords CSV (header: keyword)")
    parser.add_argument("--keyword", type=str, default=None,
                        help="Single keyword to analyze")
    parser.add_argument("--top", type=int, default=None,
                        help="Number of top gigs to collect (default: from config)")
    parser.add_argument("--resume", action="store_true",
                        help="Retry previously failed keywords")
    parser.add_argument("--force", action="store_true",
                        help="Reprocess all keywords, ignoring checkpoints")
    parser.add_argument("--max-keywords", type=int, default=None,
                        help="Maximum keywords to process in this run")
    parser.add_argument("--tier2", action="store_true",
                        help="Enable Tier 2 deep gig detail scraping")
    args = parser.parse_args()

    # Load config
    config = load_config()

    # Override config with CLI args
    if args.top:
        config.setdefault("collection", {})["top_n"] = args.top
    if args.max_keywords:
        config.setdefault("collection", {})["max_keywords_per_run"] = args.max_keywords
    if args.tier2:
        config.setdefault("collection", {})["collect_gig_details"] = True

    # Determine keywords to process
    if args.keyword:
        keywords = [args.keyword]
    else:
        keywords = load_keywords(args.input)

    # Apply max keywords limit
    max_kw = config.get("collection", {}).get("max_keywords_per_run", 0)
    if max_kw and max_kw > 0:
        keywords = keywords[:max_kw]

    if not keywords:
        print("No keywords to process.")
        sys.exit(0)

    # Set up logging
    col_logger, err_logger = setup_logging()

    # Set up checkpoint manager
    checkpoint = CheckpointManager()

    # Filter keywords based on checkpoint
    pending = checkpoint.get_pending_keywords(
        keywords, force=args.force, resume=args.resume
    )
    if not pending:
        print("All keywords already completed. Use --force to reprocess, or --resume to retry failures.")
        sys.exit(0)

    skipped = len(keywords) - len(pending)
    if skipped > 0:
        print(f"Skipping {skipped} already-completed keywords.")

    # Generate run ID
    run_id = generate_run_id()
    checkpoint.set_run_id(run_id)

    # Initialize database
    storage = StorageManager()
    storage.create_run(run_id, len(pending))

    # Initialize browser
    browser = BrowserManager(config)
    driver = browser.start()

    # Navigate to Fiverr immediately so the user can SEE the browser is working
    try:
        print("  Opening Fiverr home page...")
        driver.get("https://www.fiverr.com/")
        driver.set_window_rect(0, 0, 1280, 900)
        print("  Fiverr loaded in the visible Chrome window.")
    except Exception as e:
        print(f"  Warning: Could not pre-load Fiverr: {e}")

    # Initialize collector
    collector = FiverrCollector(
        browser, config, col_logger=col_logger, err_logger=err_logger
    )

    # Override top_n from config
    collection_config = config.get("collection", {})
    collector.top_n = collection_config.get("top_n", 20)
    collector.collect_details = collection_config.get("collect_gig_details", False)
    collector.max_detail_pages = min(collection_config.get("max_detail_pages", 10), collector.top_n)

    # Handle SIGINT (Ctrl+C) — save checkpoint before exit
    def signal_handler(sig, frame):
        print("\n\nCtrl+C detected — saving checkpoint and shutting down...")
        storage.update_run_status(run_id, "interrupted")
        browser.shutdown()
        storage.close()
        sys.exit(130)

    signal.signal(signal.SIGINT, signal_handler)

    # Process keywords
    all_gig_data = []
    all_keyword_analyses = []
    completed_count = 0
    failed_count = 0

    try:
        for i, keyword in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}] {keyword}")
            print("  Collecting SERP...", end=" ", flush=True)

            result = collector.collect_keyword(keyword)

            if result.get("error"):
                failed_count += 1
                print(f"FAILED ({result['error']})")
                checkpoint.mark_failed(keyword, result["error"])
                storage.log_error(run_id, keyword, "collection_error", result["error"])
                log_error(err_logger, keyword, "collection_error", result["error"])

                # If max challenges exceeded, end run
                if result["error"] == "max_challenges_exceeded":
                    print("\nMax challenges exceeded — ending run.")
                    break

                # Continue to next keyword
                continue

            gig_count = len(result.get("gigs", []))
            print(f"found {gig_count} gigs")

            # Save to database (transactional per keyword)
            save_ok = storage.save_keyword_results(run_id, keyword, result)
            if not save_ok:
                print("  WARNING: Failed to save to database")

            # Mark as completed in checkpoint
            checkpoint.mark_completed(keyword, gig_count)
            completed_count += 1

            # Collect raw data for analysis
            for gig in result.get("gigs", []):
                gig["keyword"] = keyword
                all_gig_data.append(gig)

            # Run analysis for this keyword
            print("  Analyzing competitors...", end=" ", flush=True)

            gigs_data = result.get("gigs", [])
            kw_from_result = result.get("keyword", keyword)

            # Intent classification
            intent = classify_intent(keyword)

            # Demand signal
            demand = calculate_demand_signal(result.get("total_results_parsed"))

            # Relevance
            relevance = calculate_keyword_relevance(keyword, gigs_data)

            # Competition & SERP concentration
            competition = analyze_competition(gigs_data)
            serp = analyze_serp_concentration(gigs_data)

            # Override exact keyword saturation in competition
            competition["exact_keyword_saturation"] = relevance["exact_title_match_pct"]
            competition["title_optimization_saturation"] = relevance["partial_title_match_pct"]

            # Gig-level scores
            analysis_weights = config.get("analysis", {})
            gig_scores = []
            for gig in gigs_data:
                scores = compute_gig_scores(gig, keyword)
                scores["title"] = gig.get("title_normalized", "")
                scores["serp_position"] = gig.get("serp_position")
                gig_scores.append(scores)

            # Competitor extremes
            extremes = per_keyword_competitor_extremes(gigs_data)

            # Title term analysis
            terms = analyze_title_terms(gigs_data)

            # Underserved services
            underserved = identify_underserved_services(keyword, gigs_data)

            # Opportunity score
            opportunity = compute_opportunity_score(
                demand_score=demand["demand_score"],
                intent_score=intent["intent_numeric"],
                relevance_score=relevance["relevance_score"],
                competition_score=competition["competition_score"],
                serp_strength_score=serp["serp_strength_score"],
                weights={
                    "demand": analysis_weights.get("demand_weight", 0.25),
                    "intent": analysis_weights.get("intent_weight", 0.20),
                    "relevance": analysis_weights.get("relevance_weight", 0.20),
                    "competition": analysis_weights.get("competition_weight", 0.25),
                    "serp_weakness": analysis_weights.get("serp_weakness_weight", 0.10),
                },
            )

            # Compile full keyword analysis
            keyword_analysis = {
                "keyword": keyword,
                "url": result.get("url", ""),
                "collection_timestamp": result.get("collection_timestamp", ""),
                "status": "completed",
                # Intent
                "primary_intent": intent["primary_intent"],
                "intent_scores": intent["scores"],
                "intent_score": intent["intent_numeric"],
                # Demand
                "total_results": result.get("total_results_parsed"),
                "total_results_raw": result.get("total_results_raw"),
                "demand_signal": demand["demand_signal"],
                "demand_score": demand["demand_score"],
                # Relevance
                "exact_title_match_pct": relevance["exact_title_match_pct"],
                "partial_title_match_pct": relevance["partial_title_match_pct"],
                "token_match_pct": relevance["token_match_pct"],
                "avg_token_match_ratio": relevance["avg_token_match_ratio"],
                "clearly_offering_pct": relevance["clearly_offering_pct"],
                "relevance_score": relevance["relevance_score"],
                # Competition
                "gig_count": competition["gig_count"],
                "median_reviews": competition["median_reviews"],
                "median_rating": competition["median_rating"],
                "review_distribution": competition["review_distribution"],
                "seller_level_distribution": competition["seller_level_distribution"],
                "exact_keyword_saturation": competition["exact_keyword_saturation"],
                "title_optimization_saturation": competition["title_optimization_saturation"],
                "established_seller_concentration": competition["established_seller_concentration"],
                "top5_vs_bottom15_strength": competition["top5_vs_bottom15_strength"],
                "competition_score": competition["competition_score"],
                # SERP concentration
                "top5_review_share": serp["top5_review_share"],
                "top10_review_share": serp["top10_review_share"],
                "median_review_count": serp["median_review_count"],
                "p75_review_count": serp["p75_review_count"],
                "p90_review_count": serp["p90_review_count"],
                "seller_strength_concentration": serp["seller_strength_concentration"],
                "serp_strength_score": serp["serp_strength_score"],
                # Opportunity
                "opportunity_score": opportunity["opportunity_score"],
                "demand_score": opportunity["demand_score"],
                "intent_score": opportunity["intent_score"],
                "relevance_score": opportunity["relevance_score"],
                "competition_score": opportunity["competition_score"],
                "competition_inverse_score": opportunity["competition_inverse_score"],
                "serp_strength_score": opportunity["serp_strength_score"],
                "serp_weakness_score": opportunity["serp_weakness_score"],
                "weights_used": opportunity["weights_used"],
                # Gig-level data
                "gig_scores": gig_scores,
                # Gap analysis
                "competitor_extremes": extremes,
                "title_terms": terms,
                "underserved_services": underserved,
                "data_quality": "calculated",
            }

            all_keyword_analyses.append(keyword_analysis)

            print(f"Opportunity Score: {keyword_analysis['opportunity_score']}")
            print("  Saved.")

            # Random pause between keywords (except last)
            if i < len(pending):
                collector.interaction.between_keyword_pause(
                    collector.keyword_pause_min,
                    collector.keyword_pause_max,
                )

    except KeyboardInterrupt:
        print("\n\nInterrupted. Saving progress...")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        log_error(err_logger, "GLOBAL", "fatal_error", str(e)[:500])

    finally:
        # Close browser
        browser.shutdown()

        # Update run status
        storage.update_run_status(
            run_id, "completed", completed_count, failed_count
        )

        # Verify data was collected
        if all_keyword_analyses:
            # Cluster keywords
            print("\nClustering keywords...")
            kw_list = [a["keyword"] for a in all_keyword_analyses]
            c = cluster_keywords(kw_list)
            named_clusters = name_clusters(c)

            # Assign cluster names to analyses
            for analysis in all_keyword_analyses:
                for cid, cdata in named_clusters.items():
                    if analysis["keyword"] in cdata["keywords"]:
                        analysis["cluster_name"] = cdata["name"]
                        analysis["cluster_id"] = cid
                        break
        else:
            named_clusters = {}

        # Generate reports
        print("\nGenerating reports...")

        if all_keyword_analyses:
            export_keyword_summary(all_keyword_analyses)
            export_top20_gigs(all_gig_data)
            export_competitor_analysis(all_keyword_analyses)
            export_keyword_opportunities(all_keyword_analyses)

            errors = [
                {
                    "keyword": e.get("keyword", ""),
                    "error_type": e.get("error_type", ""),
                    "error_detail": e.get("error_detail", ""),
                    "timestamp": e.get("timestamp", ""),
                }
                for e in storage.get_errors(run_id)
            ]

            run_info = storage.get_run_info(run_id)
            if run_info is None:
                run_info = {
                    "run_id": run_id,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "total_keywords": len(pending),
                    "completed_keywords": completed_count,
                    "failed_keywords": failed_count,
                    "status": "completed",
                }

            generate_excel(all_keyword_analyses, all_gig_data,
                           named_clusters, errors, run_info)
            export_results_json(all_keyword_analyses, all_gig_data,
                                named_clusters, errors, run_info)

            # Generate competitive intelligence report (if detail scraping was enabled)
            if (collection_config.get("collect_gig_details") and
                collection_config.get("generate_competitive_report", True) and
                all_keyword_analyses):

                print("\nGenerating Competitive Intelligence Report...")
                from analysis.competitive_intel import (
                    title_word_frequency, pricing_by_seller_level,
                    feature_gap_matrix, faq_topic_summary,
                    review_sentiment_analysis, underserved_opportunities
                )

                for analysis in all_keyword_analyses[:5]:  # Top 5 keywords
                    kw = analysis["keyword"]
                    kw_gigs = [g for g in all_gig_data if g.get("keyword") == kw]
                    if not kw_gigs:
                        continue

                    intel = {
                        "title_words": title_word_frequency(kw_gigs, top_n=20),
                        "pricing_levels": pricing_by_seller_level(kw_gigs),
                        "feature_gaps": feature_gap_matrix(kw_gigs),
                        "faq_topics": faq_topic_summary(kw_gigs),
                        "sentiment": review_sentiment_analysis(kw_gigs),
                        "opportunities": underserved_opportunities(kw_gigs, kw),
                    }

                    report_path = generate_competitive_report(kw, kw_gigs, intel)
                    if report_path:
                        print(f"  Competitive report saved: {report_path}")
                    else:
                        print(f"  Competitive report generated for: {kw}")

            # Gap analysis reporting
            print("\nOpportunity gaps identified:")
            gaps = find_opportunity_gaps(all_keyword_analyses)
            if gaps:
                for gap in gaps[:5]:
                    print(f"  - {gap['keyword']}: {gap['description']}")
            else:
                print("  (none found)")

        # Summary
        print("\n" + "=" * 60)
        print("RUN SUMMARY")
        print(f"  Run ID: {run_id}")
        print(f"  Keywords processed: {completed_count + failed_count}")
        print(f"  Completed: {completed_count}")
        print(f"  Failed: {failed_count}")
        if all_gig_data:
            print(f"  Gigs collected: {len(all_gig_data)}")
        print("=" * 60 + "\n")

        # Close database
        storage.close()


if __name__ == "__main__":
    main()