"""Gap analysis for Fiverr SERP keywords.

Identifies opportunities: frequent vs rare terms in top titles, underserved
services, niche modifiers, lower-competition combinations, and keywords with
high intent but comparatively weak SERPs.
"""

import re
from collections import Counter, defaultdict
from utils.normalization import tokenize, normalize_title


def analyze_title_terms(gigs_data: list) -> dict:
    """Analyze term frequency in top gig titles.

    Returns dict with frequent_terms, rare_terms, and term_stats.
    """
    if not gigs_data:
        return {"frequent_terms": [], "rare_terms": [], "term_stats": {}}

    all_tokens = []
    gig_token_sets = []

    for gig in gigs_data:
        title = gig.get("title_normalized", "") or ""
        tokens = tokenize(title)
        all_tokens.extend(tokens)
        gig_token_sets.append(tokens)

    # Count term frequency across gigs
    term_gig_count = Counter()
    for tokens in gig_token_sets:
        unique_tokens = set(tokens)
        for t in unique_tokens:
            term_gig_count[t] += 1

    total_gigs = len(gigs_data)

    # Frequent terms: appear in >50% of gigs
    frequent = [
        {"term": term, "count": count, "pct": round(count / total_gigs * 100, 1)}
        for term, count in term_gig_count.most_common(30)
        if count > total_gigs * 0.5
    ]

    # Rare terms: appear in only 1 gig
    rare = [
        {"term": term, "count": count, "pct": round(count / total_gigs * 100, 1)}
        for term, count in term_gig_count.items()
        if count == 1
    ]
    rare = sorted(rare, key=lambda x: x["term"])[:30]

    return {
        "frequent_terms": frequent,
        "rare_terms": rare,
        "term_stats": {
            "total_unique_terms": len(term_gig_count),
            "total_gigs": total_gigs,
        },
    }


def identify_underserved_services(keyword: str, gigs_data: list) -> list:
    """Identify potentially underserved service angles for a keyword.

    Looks for gaps where the keyword has high intent but the SERP shows
    weaker competition in specific sub-niches.
    """
    opportunities = []

    if not gigs_data:
        return opportunities

    # Check for missing service modifiers in titles
    service_modifiers = [
        "custom", "automated", "api", "real-time", "bulk", "enterprise",
        "managed", "cloud-based", "scalable", "fast", "accurate",
        "affordable", "professional", "expert", "dedicated",
    ]

    title_texts = " ".join(
        gig.get("title_normalized", "") or "" for gig in gigs_data
    ).lower()

    for modifier in service_modifiers:
        if modifier not in title_texts:
            opportunities.append({
                "type": "missing_modifier",
                "modifier": modifier,
                "description": f"No gigs use '{modifier}' in title — potential differentiator",
            })

    # Check for low-review positions (easier to outrank)
    low_review_positions = []
    for gig in gigs_data:
        reviews = gig.get("review_count_cleaned", "")
        try:
            rv = int(float(reviews)) if reviews else None
        except (ValueError, TypeError):
            rv = None
        if rv is not None and rv < 50:
            low_review_positions.append({
                "position": gig.get("serp_position"),
                "title": gig.get("title_normalized", "")[:80],
                "reviews": rv,
            })

    if low_review_positions:
        opportunities.append({
            "type": "low_review_positions",
            "count": len(low_review_positions),
            "positions": low_review_positions,
            "description": f"{len(low_review_positions)} positions have <50 reviews — easier to compete",
        })

    return opportunities


def find_opportunity_gaps(keyword_analyses: list) -> list:
    """Find keywords with high intent but comparatively weak SERPs.

    These are the best opportunity gaps — high buyer intent keywords
    where the current competition is relatively weak.

    Args:
        keyword_analyses: List of dicts with keyword analysis results.

    Returns list of gap opportunities sorted by opportunity score.
    """
    gaps = []

    for analysis in keyword_analyses:
        intent = analysis.get("intent_score", 0)
        competition = analysis.get("competition_score", 50)
        serp_strength = analysis.get("serp_strength_score", 50)
        opportunity = analysis.get("opportunity_score", 0)

        # High intent + low competition = strong gap
        if intent >= 60 and competition <= 40:
            gaps.append({
                "keyword": analysis.get("keyword"),
                "type": "high_intent_low_competition",
                "intent_score": intent,
                "competition_score": competition,
                "opportunity_score": opportunity,
                "description": "High buyer intent with low competition — strong opportunity",
            })
        # High intent + weak SERP = gap
        elif intent >= 50 and serp_strength <= 35:
            gaps.append({
                "keyword": analysis.get("keyword"),
                "type": "high_intent_weak_serp",
                "intent_score": intent,
                "serp_strength_score": serp_strength,
                "opportunity_score": opportunity,
                "description": "High intent but SERP dominated by weak sellers — opportunity to enter",
            })

    return sorted(gaps, key=lambda x: x["opportunity_score"], reverse=True)


def per_keyword_competitor_extremes(gigs_data: list) -> dict:
    """Identify strongest, weakest, and most optimized competitors per keyword.

    Returns dict with extremes.
    """
    if not gigs_data:
        return {
            "strongest_competitor": None,
            "weakest_competitor": None,
            "most_optimized_title": None,
            "highest_review_competitor": None,
            "lowest_review_competitor": None,
        }

    def _safe_int(val):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    # Find extremes
    strongest = max(
        gigs_data,
        key=lambda g: _safe_int(g.get("review_count_cleaned", 0)),
        default=None,
    )
    weakest = min(
        gigs_data,
        key=lambda g: _safe_int(g.get("review_count_cleaned", 999999)),
        default=None,
    )
    highest_review = max(
        gigs_data,
        key=lambda g: _safe_int(g.get("review_count_cleaned", 0)),
        default=None,
    )
    lowest_review = min(
        gigs_data,
        key=lambda g: _safe_int(g.get("review_count_cleaned", 999999)),
        default=None,
    )

    # Most optimized title: longest title with most keyword tokens
    most_optimized = max(
        gigs_data,
        key=lambda g: len((g.get("title_normalized") or "").split()),
        default=None,
    )

    def _format(gig):
        if not gig:
            return None
        return {
            "title": (gig.get("title_normalized") or "")[:100],
            "reviews": gig.get("review_count_cleaned"),
            "rating": gig.get("seller_rating_normalized"),
            "position": gig.get("serp_position"),
        }

    return {
        "strongest_competitor": _format(strongest),
        "weakest_competitor": _format(weakest),
        "most_optimized_title": _format(most_optimized),
        "highest_review_competitor": _format(highest_review),
        "lowest_review_competitor": _format(lowest_review),
    }