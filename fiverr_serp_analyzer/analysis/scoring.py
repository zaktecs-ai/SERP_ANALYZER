"""Opportunity scoring engine for Fiverr SERP keywords.

Transparent, configurable weighted scoring. Every formula is documented.
All scores are 0-100. Higher opportunity = better keyword to target.
"""


def compute_opportunity_score(
    demand_score: float,
    intent_score: float,
    relevance_score: float,
    competition_score: float,
    serp_strength_score: float,
    weights: dict = None,
) -> dict:
    """Compute the weighted Opportunity Score for a keyword.

    Args:
        demand_score: 0-100 demand signal score.
        intent_score: 0-100 buyer intent score.
        relevance_score: 0-100 keyword relevance score.
        competition_score: 0-100 competition strength (higher = harder).
        serp_strength_score: 0-100 SERP concentration (higher = stronger SERP).
        weights: Configurable weight dict with keys:
            demand, intent, relevance, competition, serp_weakness.

    Returns dict with all component scores and the final opportunity score.

    Formula:
        opportunity = demand * w_demand
                    + intent * w_intent
                    + relevance * w_relevance
                    + (100 - competition) * w_competition
                    + (100 - serp_strength) * w_serp_weakness

    The competition and SERP strength are INVERTED because higher competition
    means lower opportunity. All components normalized to 0-100.
    """
    if weights is None:
        weights = {
            "demand": 0.25,
            "intent": 0.20,
            "relevance": 0.20,
            "competition": 0.25,
            "serp_weakness": 0.10,
        }

    # Ensure all scores are in 0-100 range
    demand = max(0, min(100, demand_score or 50))
    intent = max(0, min(100, intent_score or 50))
    relevance = max(0, min(100, relevance_score or 50))
    competition = max(0, min(100, competition_score or 50))
    serp_strength = max(0, min(100, serp_strength_score or 50))

    # Invert competition and SERP strength for opportunity
    competition_inverse = 100 - competition
    serp_weakness = 100 - serp_strength

    # Weighted sum
    opportunity = (
        demand * weights.get("demand", 0.25)
        + intent * weights.get("intent", 0.20)
        + relevance * weights.get("relevance", 0.20)
        + competition_inverse * weights.get("competition", 0.25)
        + serp_weakness * weights.get("serp_weakness", 0.10)
    )

    return {
        "demand_score": round(demand, 1),
        "intent_score": round(intent, 1),
        "relevance_score": round(relevance, 1),
        "competition_score": round(competition, 1),
        "competition_inverse_score": round(competition_inverse, 1),
        "serp_strength_score": round(serp_strength, 1),
        "serp_weakness_score": round(serp_weakness, 1),
        "opportunity_score": round(opportunity, 1),
        "weights_used": weights,
        "data_quality": "calculated",
    }


def compute_gig_scores(gig_data: dict, keyword: str) -> dict:
    """Compute per-gig analysis scores.

    Args:
        gig_data: Dict with gig fields.
        keyword: The search keyword.

    Returns dict with gig-level scores.
    """
    from utils.normalization import keyword_token_match, parse_number, parse_rating

    title = gig_data.get("title_normalized", "") or ""

    # Title optimization score
    match_data = keyword_token_match(keyword, title)
    title_opt_score = match_data["token_match_ratio"] * 100

    # Keyword relevance score
    kw_rel_score = title_opt_score  # Same as title optimization for now

    # Seller strength score
    reviews = parse_number(gig_data.get("review_count_cleaned", ""))
    rating = parse_rating(gig_data.get("seller_rating_normalized", ""))

    seller_strength = 50.0
    if reviews is not None:
        if reviews > 1000:
            seller_strength = 95
        elif reviews > 500:
            seller_strength = 85
        elif reviews > 100:
            seller_strength = 70
        elif reviews > 50:
            seller_strength = 55
        elif reviews > 10:
            seller_strength = 40
        else:
            seller_strength = 20

    # Review strength
    review_strength = 50.0
    if reviews is not None:
        if reviews > 1000:
            review_strength = 95
        elif reviews > 500:
            review_strength = 85
        elif reviews > 100:
            review_strength = 70
        elif reviews > 50:
            review_strength = 55
        elif reviews > 10:
            review_strength = 40
        else:
            review_strength = 20

    # Rating strength
    rating_strength = 50.0
    if rating is not None:
        rating_strength = (rating / 5.0) * 100

    # Price positioning (normalized, lower = more competitive pricing)
    price = parse_number(gig_data.get("starting_price_normalized", ""))
    price_positioning = 50.0
    if price is not None and price > 0:
        if price < 20:
            price_positioning = 90  # very competitive pricing
        elif price < 50:
            price_positioning = 75
        elif price < 100:
            price_positioning = 55
        elif price < 200:
            price_positioning = 35
        else:
            price_positioning = 15

    return {
        "title_optimization_score": round(title_opt_score, 1),
        "keyword_relevance_score": round(kw_rel_score, 1),
        "seller_strength_score": round(seller_strength, 1),
        "review_strength_score": round(review_strength, 1),
        "rating_strength_score": round(rating_strength, 1),
        "price_positioning_score": round(price_positioning, 1),
        "serp_position": gig_data.get("serp_position"),
        "data_quality": "calculated",
    }


def rank_keywords_by_opportunity(keyword_analyses: list) -> list:
    """Sort keyword analyses by opportunity score (descending).

    Args:
        keyword_analyses: List of dicts, each with at least 'keyword' and
                          'opportunity_score'.

    Returns sorted list.
    """
    return sorted(
        keyword_analyses,
        key=lambda x: x.get("opportunity_score", 0),
        reverse=True,
    )