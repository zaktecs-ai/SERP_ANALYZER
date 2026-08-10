"""Keyword-level analysis: intent classification, relevance, demand signals."""

import re
from utils.normalization import normalize_title, tokenize, keyword_token_match


# Intent classification patterns
INTENT_PATTERNS = {
    "transactional": [
        r"\b(buy|purchase|order|hire|get|find|cheap|affordable|best price|for sale)\b",
        r"\b(need|want|looking for)\b",
    ],
    "commercial": [
        r"\b(review|comparison|best|top|vs|versus|alternative|cheap|affordable)\b",
        r"\b(service|services|provider|agency|expert|professional)\b",
    ],
    "service_specific": [
        r"\b(scrap(e|ing|er)|extract(ion|or)?|data|web|crawl(er|ing)?)\b",
        r"\b(python|selenium|beautifulsoup|playwright|api|automation)\b",
        r"\b(custom|bespoke|tailored|specific)\b",
    ],
    "informational": [
        r"\b(how|what|why|when|guide|tutorial|learn|example|tips)\b",
    ],
    "niche_service": [
        r"\b(google maps|ecommerce|real estate|lead generation|product)\b",
        r"\b(business listings|linkedin|instagram|twitter|facebook)\b",
    ],
}


def classify_intent(keyword: str) -> dict:
    """Classify buyer intent for a keyword using rule-based NLP.

    Returns dict with:
        primary_intent: str
        scores: dict of intent -> score (0-1)
        intent_numeric: float (0-100, higher = more commercial/transactional)
    """
    kw_lower = keyword.lower().strip()
    scores = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0.0
        for pattern in patterns:
            matches = re.findall(pattern, kw_lower)
            if matches:
                score += len(matches) * 0.5
        scores[intent] = min(score, 1.0)

    # Determine primary intent.
    # service_specific is the "default" category for this tool's domain
    # (most keywords are scraping-related). Explicit signals like
    # transactional or informational should take priority.
    primary = "ambiguous"
    max_score = 0.0
    # Priority: informational > transactional > commercial > service_specific > niche_service
    # Explicit informational/transactional signals win over the domain default.
    intent_priority = ["informational", "transactional", "commercial",
                       "service_specific", "niche_service"]
    for intent in intent_priority:
        # For service_specific (the domain default), require a higher score to win
        # against explicit signals already found.
        if intent == "service_specific":
            if scores.get(intent, 0) > max_score and max_score == 0:
                primary = intent
                max_score = scores[intent]
        else:
            if scores.get(intent, 0) > max_score:
                max_score = scores[intent]
                primary = intent
            elif scores.get(intent, 0) == max_score and max_score > 0:
                # Tie: explicit signal wins over service_specific
                if intent in ("informational", "transactional"):
                    primary = intent

    # Numeric intent score (0-100): transactional/service_specific = high
    intent_numeric = 0.0
    intent_numeric += scores.get("transactional", 0) * 40
    intent_numeric += scores.get("service_specific", 0) * 35
    intent_numeric += scores.get("commercial", 0) * 15
    intent_numeric += scores.get("niche_service", 0) * 10
    intent_numeric += scores.get("informational", 0) * 0  # informational = low buyer intent
    intent_numeric = min(intent_numeric, 100.0)

    if primary == "ambiguous":
        intent_numeric = max(intent_numeric, 25.0)  # floor for ambiguous

    return {
        "primary_intent": primary,
        "scores": scores,
        "intent_numeric": round(intent_numeric, 1),
    }


def calculate_keyword_relevance(keyword: str, gigs_data: list) -> dict:
    """Calculate how closely the top gigs match the keyword.

    Args:
        keyword: The search keyword.
        gigs_data: List of dicts with at least 'title_normalized' key.

    Returns dict with relevance metrics.
    """
    if not gigs_data:
        return {
            "exact_title_match_pct": 0.0,
            "partial_title_match_pct": 0.0,
            "token_match_pct": 0.0,
            "avg_token_match_ratio": 0.0,
            "clearly_offering_pct": 0.0,
            "relevance_score": 0.0,
        }

    total = len(gigs_data)
    exact_matches = 0
    partial_matches = 0
    token_match_count = 0
    token_ratios = []
    clearly_offering = 0

    kw_tokens = tokenize(keyword)

    for gig in gigs_data:
        title = gig.get("title_normalized", "") or ""
        match_data = keyword_token_match(keyword, title)

        if match_data["exact_match"]:
            exact_matches += 1
        if match_data["token_match_ratio"] >= 0.5:
            partial_matches += 1
        if match_data["token_matches"] > 0:
            token_match_count += 1

        token_ratios.append(match_data["token_match_ratio"])

        # "Clearly offering" = at least 50% token match
        if match_data["token_match_ratio"] >= 0.5:
            clearly_offering += 1

    avg_token_ratio = sum(token_ratios) / total if token_ratios else 0.0

    # Relevance score: weighted combination
    relevance_score = (
        (exact_matches / total) * 40 +
        (partial_matches / total) * 30 +
        avg_token_ratio * 30
    )
    relevance_score = min(relevance_score, 100.0)

    return {
        "exact_title_match_pct": round((exact_matches / total) * 100, 1),
        "partial_title_match_pct": round((partial_matches / total) * 100, 1),
        "token_match_pct": round((token_match_count / total) * 100, 1),
        "avg_token_match_ratio": round(avg_token_ratio, 3),
        "clearly_offering_pct": round((clearly_offering / total) * 100, 1),
        "relevance_score": round(relevance_score, 1),
    }


def calculate_demand_signal(total_results_parsed: int) -> dict:
    """Calculate demand signal from Fiverr's visible result count.

    This is NOT search volume — it's the number of gigs Fiverr returns.
    Store raw value separately; do not treat as exact competition.
    """
    if total_results_parsed is None:
        return {
            "total_results": None,
            "demand_signal": "unknown",
            "demand_score": 50.0,  # neutral when unknown
        }

    # Rough categorization based on gig count
    if total_results_parsed < 100:
        signal = "very_low"
        score = 10.0
    elif total_results_parsed < 500:
        signal = "low"
        score = 25.0
    elif total_results_parsed < 2000:
        signal = "moderate"
        score = 50.0
    elif total_results_parsed < 10000:
        signal = "high"
        score = 75.0
    else:
        signal = "very_high"
        score = 100.0

    return {
        "total_results": total_results_parsed,
        "demand_signal": signal,
        "demand_score": score,
    }