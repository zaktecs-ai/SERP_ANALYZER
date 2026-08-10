"""JSON export for the Fiverr SERP Analyzer.

Preserves the raw structured data in results.json.
"""

import json
import os
from datetime import datetime, timezone


def export_results_json(
    keyword_analyses: list,
    all_gigs: list,
    clusters: dict,
    errors: list,
    run_info: dict,
    output_path: str = "results.json",
):
    """Export all results to a structured JSON file.

    Args:
        keyword_analyses: List of per-keyword analysis dicts.
        all_gigs: List of all gig data dicts.
        clusters: Dict of keyword clusters.
        errors: List of error dicts.
        run_info: Dict with collection run metadata.
        output_path: Output file path.
    """
    output = {
        "metadata": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "run_info": run_info,
            "total_keywords_analyzed": len(keyword_analyses),
            "total_gigs_collected": len(all_gigs),
            "total_errors": len(errors),
        },
        "keyword_analyses": keyword_analyses,
        "all_gigs": all_gigs,
        "clusters": clusters,
        "errors": errors,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"JSON results saved to: {output_path}")
    return output_path