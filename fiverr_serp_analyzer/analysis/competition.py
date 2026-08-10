"""Competition strength analysis for Fiverr SERP keywords.

Multi-signal analysis: never uses result count alone.
Uses robust statistics (median, percentiles), not just means.
"""

import statistics
import math
from utils.normalization import parse_number, parse_rating, parse_review_count


def _safe_float(value, default=None):
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=None):
    """Safely convert a value to int."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def analyze_competition(gigs_data: list) -> dict:
    """Analyze competition strength for a keyword's top gigs.

    Args:
        gigs_data: List of dicts with seller_rating_normalized,
                   review_count_cleaned, seller_level_normalized,
                   starting_price_normalized, title_normalized.

    Returns dict with competition metrics.
    """
    if not gigs_data:
        return {
            "gig_count": 0,
            "median_reviews": None,
            "median_rating": None,
            "review_distribution": {},
            "seller_level_distribution": {},
            "exact_keyword_saturation": 0.0,
            "title_optimization_saturation": 0.0,
            "established_seller_concentration": 0.0,
            "top5_vs_bottom15_strength": None,
            "competition_score": 50.0,  # neutral
        }

    total = len(gigs_data)

    # Extract numeric values
    reviews = []
    ratings = []
    prices = []
    seller_levels = []

    for g in gigs_data:
        rv = _safe_int(g.get("review_count_cleaned"))
        if rv is not None and rv >= 0:
            reviews.append(rv)

        rt = _safe_float(g.get("seller_rating_normalized"))
        if rt is not None and 0 <= rt <= 5:
            ratings.append(rt)

        pr = _safe_float(g.get("starting_price_normalized"))
        if pr is not None and pr > 0:
            prices.append(pr)

        level = (g.get("seller_level_normalized") or "").lower().strip()
        if level:
            seller_levels.append(level)

    # Median reviews
    median_reviews = statistics.median(reviews) if reviews else None

    # Median rating
    median_rating = statistics.median(ratings) if ratings else None

    # Review distribution (quartiles)
    review_dist = {}
    if reviews:
        sorted_reviews = sorted(reviews)
        review_dist = {
            "min": sorted_reviews[0],
            "p25": sorted_reviews[len(sorted_reviews) // 4] if len(sorted_reviews) >= 4 else sorted_reviews[0],
            "median": median_reviews,
            "p75": sorted_reviews[3 * len(sorted_reviews) // 4] if len(sorted_reviews) >= 4 else sorted_reviews[-1],
            "p90": sorted_reviews[9 * len(sorted_reviews) // 10] if len(sorted_reviews) >= 10 else sorted_reviews[-1],
            "max": sorted_reviews[-1],
            "mean": round(statistics.mean(reviews), 1),
        }

    # Seller level distribution
    level_dist = {}
    for l in seller_levels:
        level_dist[l] = level_dist.get(l, 0) + 1
    level_dist_pct = {k: round(v / total * 100, 1) for k, v in level_dist.items()}

    # Exact keyword saturation: % of top 20 with exact keyword in title
    # (calculated externally with keyword context, placeholder here)
    exact_saturation = 0.0

    # Title optimization saturation: % with optimized titles
    # (calculated externally, placeholder)
    title_opt_saturation = 0.0

    # Established seller concentration: % with high review counts
    if reviews and median_reviews:
        high_review_threshold = median_reviews * 2 if median_reviews > 0 else 10
        established = sum(1 for r in reviews if r >= high_review_threshold)
        established_concentration = round(established / total * 100, 1)
    else:
        established_concentration = 0.0

    # Top-5 vs bottom-15 strength
    top5_vs_bottom = None
    if len(reviews) >= 10:
        top5 = reviews[:5]
        bottom = reviews[5:20] if len(reviews) >= 20 else reviews[5:]
        top5_median = statistics.median(top5) if top5 else 0
        bottom_median = statistics.median(bottom) if bottom else 0
        if bottom_median > 0:
            top5_vs_bottom = round(top5_median / bottom_median, 2)
        else:
            top5_vs_bottom = float('inf') if top5_median > 0 else 1.0

    # Competition score (0-100, higher = more competitive)
    comp_score = 50.0  # neutral baseline

    if median_reviews is not None:
        # Higher median reviews = more competitive
        if median_reviews > 1000:
            comp_score += 25
        elif median_reviews > 500:
            comp_score += 15
        elif median_reviews > 100:
            comp_score += 5
        elif median_reviews < 10:
            comp_score -= 20
        elif median_reviews < 50:
            comp_score -= 10

    if median_rating is not None:
        # Higher median rating = more competitive
        if median_rating >= 4.9:
            comp_score += 15
        elif median_rating >= 4.7:
            comp_score += 5
        elif median_rating < 4.0:
            comp_score -= 10

    if established_concentration > 50:
        comp_score += 15
    elif established_concentration > 30:
        comp_score += 5
    elif established_concentration < 10:
        comp_score -= 10

    comp_score = max(0, min(100, comp_score))

    return {
        "gig_count": total,
        "median_reviews": median_reviews,
        "median_rating": median_rating,
        "review_distribution": review_dist,
        "seller_level_distribution": level_dist_pct,
        "exact_keyword_saturation": exact_saturation,
        "title_optimization_saturation": title_opt_saturation,
        "established_seller_concentration": established_concentration,
        "top5_vs_bottom15_strength": top5_vs_bottom,
        "competition_score": round(comp_score, 1),
    }


def analyze_serp_concentration(gigs_data: list) -> dict:
    """Analyze SERP concentration — is the SERP dominated by a few sellers?

    Returns dict with concentration metrics.
    """
    if not gigs_data:
        return {
            "top5_review_share": None,
            "top10_review_share": None,
            "median_review_count": None,
            "p75_review_count": None,
            "p90_review_count": None,
            "seller_strength_concentration": None,
            "serp_strength_score": 50.0,
        }

    reviews = []
    for g in gigs_data:
        rv = _safe_int(g.get("review_count_cleaned"))
        if rv is not None and rv >= 0:
            reviews.append(rv)

    if not reviews:
        return {
            "top5_review_share": None,
            "top10_review_share": None,
            "median_review_count": None,
            "p75_review_count": None,
            "p90_review_count": None,
            "seller_strength_concentration": None,
            "serp_strength_score": 50.0,
        }

    total_reviews = sum(reviews)
    sorted_reviews = sorted(reviews, reverse=True)

    top5_share = round(sum(sorted_reviews[:5]) / total_reviews * 100, 1) if total_reviews > 0 else 0
    top10_share = round(sum(sorted_reviews[:10]) / total_reviews * 100, 1) if total_reviews > 0 else 0

    median_rv = statistics.median(reviews)
    sorted_asc = sorted(reviews)
    n = len(sorted_asc)
    p75 = sorted_asc[3 * n // 4] if n >= 4 else sorted_asc[-1]
    p90 = sorted_asc[9 * n // 10] if n >= 10 else sorted_asc[-1]

    # Seller strength concentration: ratio of top-5 to total
    seller_concentration = top5_share

    # SERP strength score (0-100, higher = stronger/more concentrated SERP)
    serp_score = 50.0
    if top5_share > 80:
        serp_score += 30
    elif top5_share > 60:
        serp_score += 15
    elif top5_share > 40:
        serp_score += 5
    elif top5_share < 20:
        serp_score -= 15

    if median_rv > 500:
        serp_score += 15
    elif median_rv > 100:
        serp_score += 5
    elif median_rv < 10:
        serp_score -= 15

    serp_score = max(0, min(100, serp_score))

    return {
        "top5_review_share": top5_share,
        "top10_review_share": top10_share,
        "median_review_count": median_rv,
        "p75_review_count": p75,
        "p90_review_count": p90,
        "seller_strength_concentration": seller_concentration,
        "serp_strength_score": round(serp_score, 1),
    }