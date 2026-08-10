from __future__ import annotations
"""Cross-gig competitive intelligence analysis.

Operates on arrays of gig data — either SERP-level Tier-1 records or
Tier-2 detail-page records — and produces aggregate insights suitable for
competitive report generation.

No external ML/NLP libraries.  Everything is built from word-frequency
analysis, pattern matching, and basic statistical aggregation.
"""

import re
import math
from collections import Counter, defaultdict
from utils.normalization import (
    normalize_text, normalize_title, tokenize, parse_number, parse_price,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Common English stop words filtered out of frequency analysis
_STOP_WORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
    "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves", "what", "which",
    "who", "whom", "this", "that", "these", "those", "am", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if",
    "or", "because", "as", "until", "while", "of", "at", "by", "for",
    "with", "about", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "in", "out", "on", "off",
    "over", "under", "again", "further", "then", "once", "here", "there",
    "when", "where", "why", "how", "all", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "can", "will", "just", "don",
    "should", "now", "up", "down", "also", "get", "one", "would", "could",
    "make", "like", "just", "really", "use", "using", "used",
}

_SENTIMENT_POSITIVE = {
    "excellent", "great", "amazing", "perfect", "fantastic", "outstanding",
    "wonderful", "professional", "impressive", "recommend", "pleased",
    "happy", "incredible", "superb", "brilliant", "exceptional", "best",
    "awesome", "love", "loved", "helpful", "quick", "fast", "responsive",
    "quality", "exceeded", "patient", "understanding", "top", "detailed",
    "easy", "smooth", "timely", "polite", "kind", "friendly",
    "knowledgeable", "skilled", "talented", "genius",
}

_SENTIMENT_NEGATIVE = {
    "disappointed", "bad", "poor", "terrible", "awful", "horrible",
    "waste", "slow", "unresponsive", "rude", "unprofessional", "wrong",
    "mistake", "error", "failed", "failure", "never", "refund",
    "complaint", "issue", "problem", "frustrating", "frustrated",
    "useless", "overpriced", "scam", "avoid", "warning",
    "incomplete", "missing", "late", "delay", "delayed", "ignored",
}

_PRICE_TIERS = {
    "budget": (0, 25),
    "mid": (25, 75),
    "premium": (75, 200),
    "enterprise": (200, float("inf")),
}


def _extract_title(gig: dict) -> str:
    """Get the gig title from either a flat or nested gig record."""
    # Flat (Tier 1)
    t = gig.get("title_normalized") or gig.get("title")
    if t and isinstance(t, str):
        return t
    # Nested (parsers format)
    title_obj = gig.get("title", {})
    if isinstance(title_obj, dict):
        t = title_obj.get("normalized") or title_obj.get("raw")
        if t and isinstance(t, str):
            return t
    return ""


def _extract_price(gig: dict):  # -> Optional[float]
    """Get the gig price from either a flat or nested gig record."""
    # Flat (Tier 1)
    p = gig.get("starting_price_normalized")
    if p is not None:
        return parse_price(str(p))
    # Nested (parsers format)
    price_obj = gig.get("starting_price", {})
    if isinstance(price_obj, dict):
        p = price_obj.get("normalized") or price_obj.get("raw")
        if p:
            return parse_price(str(p))
    # Tier 2 packages — use the first package price
    packages = gig.get("packages", [])
    if packages and isinstance(packages, list):
        first_pkg = packages[0]
        if isinstance(first_pkg, dict):
            p = first_pkg.get("price")
            if p is not None:
                return float(p) if isinstance(p, (int, float)) else parse_price(str(p))
    return None


def _extract_level(gig: dict) -> str:
    """Get the seller level from a gig record."""
    # Flat
    lvl = gig.get("seller_level_normalized")
    if lvl and isinstance(lvl, str):
        return lvl.strip().lower()
    # Nested
    level_obj = gig.get("seller_level", {})
    if isinstance(level_obj, dict):
        lvl = level_obj.get("normalized") or level_obj.get("raw")
        if lvl and isinstance(lvl, str):
            return lvl.strip().lower()
    return "unknown"


def _extract_reviews(gig: dict) -> list:
    """Get review texts from a Tier-2 gig record."""
    reviews = gig.get("recent_reviews", [])
    if not isinstance(reviews, list):
        return []
    return reviews


def _extract_faq(gig: dict) -> list:
    """Get FAQ entries from a Tier-2 gig record."""
    faq = gig.get("faq", [])
    if not isinstance(faq, list):
        return []
    return faq


def _extract_tags(gig: dict) -> list:
    """Get tag strings from a gig record."""
    # Tier 2
    tags = gig.get("tags", [])
    if isinstance(tags, list) and tags:
        return tags
    # Tier 1 (service_tags)
    st = gig.get("service_tags", {})
    if isinstance(st, dict):
        tags = st.get("normalized") or st.get("raw") or []
        if isinstance(tags, list):
            return tags
    return []


def _extract_features(gig: dict) -> list:
    """Get all features across all packages in a Tier-2 gig record."""
    packages = gig.get("packages", [])
    if not isinstance(packages, list):
        return []
    all_features = []
    for pkg in packages:
        if isinstance(pkg, dict):
            feats = pkg.get("features", [])
            if isinstance(feats, list):
                all_features.extend(feats)
    return all_features


def _filter_stopwords(tokens: set) -> set:
    """Remove common stop words from a set of tokens."""
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 1}


# ---------------------------------------------------------------------------
# Public analysis functions
# ---------------------------------------------------------------------------

def title_word_frequency(gigs: list, top_n: int = 20) -> list:
    """Compute word frequency across all gig titles.

    Args:
        gigs: List of gig dicts (Tier 1 or Tier 2).
        top_n: Number of top words to return.

    Returns:
        List of {word, count, pct} sorted by descending count.
    """
    if not gigs:
        return []

    word_counter = Counter()
    total_gigs = 0

    for gig in gigs:
        title = _extract_title(gig)
        if not title:
            continue
        total_gigs += 1
        tokens = tokenize(title)
        filtered = _filter_stopwords(tokens)
        for word in filtered:
            word_counter[word] += 1

    results = []
    for word, count in word_counter.most_common(top_n):
        results.append({
            "word": word,
            "count": count,
            "pct": round(count / total_gigs * 100, 1) if total_gigs else 0.0,
        })
    return results


def pricing_by_seller_level(gigs: list) -> dict:
    """Aggregate pricing statistics grouped by seller level.

    Args:
        gigs: List of gig dicts with price and seller_level info.

    Returns:
        {level_name: {avg_price, min_price, max_price, count}}
    """
    if not gigs:
        return {}

    buckets = defaultdict(list)
    for gig in gigs:
        price = _extract_price(gig)
        level = _extract_level(gig)
        if price is not None and price > 0:
            buckets[level].append(price)

    result = {}
    for level, prices in sorted(buckets.items()):
        if not prices:
            continue
        result[level] = {
            "avg_price": round(sum(prices) / len(prices), 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "count": len(prices),
        }
    return result


def feature_gap_matrix(gigs: list) -> dict:
    """Analyse which features appear across gigs and their price correlation.

    Each feature is normalised (lowered, trimmed) so that small wording
    variations are collapsed.

    Args:
        gigs: List of Tier-2 gig dicts with packages[].features.

    Returns:
        {canonical_feature_name: {present_in_pct, avg_price_when_present}}
    """
    if not gigs:
        return {}

    # Collect all features across all gigs with price info
    # feature_name -> list of prices for gigs that include it
    feature_prices = defaultdict(list)
    total_gigs_with_features = 0

    for gig in gigs:
        features = _extract_features(gig)
        price = _extract_price(gig)
        if not features:
            continue
        total_gigs_with_features += 1

        # Normalise each feature
        seen_in_gig = set()
        for feat in features:
            canonical = normalize_text(feat).lower()
            if not canonical or canonical in seen_in_gig:
                continue
            seen_in_gig.add(canonical)

            if price is not None and price > 0:
                feature_prices[canonical].append(price)
            else:
                # Still track presence even without price
                feature_prices[canonical].append(None)

    result = {}
    for feat, prices in sorted(feature_prices.items(),
                                key=lambda x: len([p for p in x[1] if p is not None]),
                                reverse=True):
        valid_prices = [p for p in prices if p is not None]
        presence = len(prices)  # total gigs this feature was seen in
        result[feat] = {
            "present_in_pct": round(presence / total_gigs_with_features * 100, 1)
            if total_gigs_with_features else 0.0,
            "avg_price_when_present": round(sum(valid_prices) / len(valid_prices), 2)
            if valid_prices else None,
        }
    return result


def faq_topic_summary(gigs: list) -> list:
    """Summarise common FAQ topics across all gigs.

    Groups questions by shared keywords and returns the most-discussed
    topics with example questions.

    Args:
        gigs: List of Tier-2 gig dicts with faq entries.

    Returns:
        [{topic, mention_count, example_questions}]
    """
    if not gigs:
        return []

    # Collect all questions
    all_questions = []
    for gig in gigs:
        faq = _extract_faq(gig)
        for entry in faq:
            q = entry.get("question") if isinstance(entry, dict) else None
            if q and q.strip():
                all_questions.append(q.strip())

    if not all_questions:
        return []

    # Tokenize each question and cluster by keyword overlap
    q_tokens = []
    for q in all_questions:
        tokens = _filter_stopwords(tokenize(q))
        q_tokens.append((q, tokens))

    # Find frequent topic keywords
    keyword_counter = Counter()
    for _, tokens in q_tokens:
        for t in tokens:
            keyword_counter[t] += 1

    # Take the top keywords as "topics"
    top_keywords = keyword_counter.most_common(15)

    results = []
    for keyword, mention_count in top_keywords:
        # Find example questions that contain this keyword
        examples = []
        for q, tokens in q_tokens:
            if keyword in tokens and q not in examples:
                examples.append(q)
            if len(examples) >= 3:
                break
        results.append({
            "topic": keyword,
            "mention_count": mention_count,
            "example_questions": examples,
        })

    return results


def review_sentiment_analysis(gigs: list) -> dict:
    """Analyse sentiment across all recent buyer reviews.

    Uses lexicon-based scoring: positive words +1, negative words -1.
    Normalises the score to a rough -1..+1 range per review, then
    averages across all reviews.

    Args:
        gigs: List of Tier-2 gig dicts with recent_reviews.

    Returns:
        {praise_words: [...], complaint_words: [...], avg_sentiment_score: float}
    """
    if not gigs:
        return {
            "praise_words": [],
            "complaint_words": [],
            "avg_sentiment_score": None,
        }

    all_praise = Counter()
    all_complaints = Counter()
    review_scores = []

    for gig in gigs:
        reviews = _extract_reviews(gig)
        for review in reviews:
            text = review.get("text") if isinstance(review, dict) else None
            if not text:
                continue

            tokens = tokenize(text)
            positive_count = 0
            negative_count = 0

            for t in tokens:
                if t in _SENTIMENT_POSITIVE:
                    positive_count += 1
                    all_praise[t] += 1
                if t in _SENTIMENT_NEGATIVE:
                    negative_count += 1
                    all_complaints[t] += 1

            total = positive_count + negative_count
            if total > 0:
                # Normalise to [-1, 1]
                score = (positive_count - negative_count) / total
            else:
                score = 0.0
            review_scores.append(score)

    avg_score = (
        round(sum(review_scores) / len(review_scores), 3)
        if review_scores else None
    )

    return {
        "praise_words": [w for w, _ in all_praise.most_common(20)],
        "complaint_words": [w for w, _ in all_complaints.most_common(20)],
        "avg_sentiment_score": avg_score,
    }


def underserved_opportunities(gigs: list, keyword: str = "") -> list:
    """Identify potentially underserved niches or gaps within the SERP.

    Uses multiple signals:
      1. Service angles / modifiers missing from titles
      2. Price gaps — tiers with low seller count
      3. Feature gaps — features that few sellers mention
      4. Quality gaps — if all top gigs have low ratings / few reviews

    Args:
        gigs: List of Tier-1 or Tier-2 gig dicts.
        keyword: The search keyword for context.

    Returns:
        [{signal_type, description, confidence}]
    """
    opportunities = []

    if not gigs:
        return [{
            "signal_type": "empty_serp",
            "description": f"No gigs found for '{keyword}' — wide-open opportunity.",
            "confidence": 0.9,
        }]

    total = len(gigs)

    # --- Signal 1: Missing service modifiers in titles ---
    service_modifiers = [
        "custom", "automated", "api", "real-time", "bulk", "enterprise",
        "managed", "cloud-based", "scalable", "fast", "accurate",
        "affordable", "professional", "expert", "dedicated",
        "premium", "express", "unlimited", "white-label", "setup",
        "integration", "consultation", "strategy", "audit",
    ]

    all_title_tokens = set()
    for gig in gigs:
        title = _extract_title(gig)
        all_title_tokens.update(tokenize(title))

    for modifier in service_modifiers:
        if modifier not in all_title_tokens:
            opportunities.append({
                "signal_type": "missing_title_modifier",
                "description": (
                    f"No gig in the top {total} uses '{modifier}' in its title. "
                    f"A '{modifier} {keyword}' gig could stand out."
                ),
                "confidence": 0.5,
            })

    # --- Signal 2: Price tier gaps ---
    prices = []
    for gig in gigs:
        p = _extract_price(gig)
        if p is not None and p > 0:
            prices.append(p)

    if prices:
        tier_counts = defaultdict(int)
        for p in prices:
            for tier_name, (lo, hi) in _PRICE_TIERS.items():
                if lo <= p < hi:
                    tier_counts[tier_name] += 1
                    break

        for tier_name in ["premium", "enterprise"]:
            count = tier_counts.get(tier_name, 0)
            pct = count / len(prices) * 100
            if pct < 15:
                opportunities.append({
                    "signal_type": "price_tier_gap",
                    "description": (
                        f"Only {count}/{len(prices)} gigs ({pct:.0f}%) are in the "
                        f"{tier_name} price range. A higher-value offering could "
                        f"capture this underserved bracket."
                    ),
                    "confidence": 0.55,
                })

    # --- Signal 3: Low seller levels ---
    levels = [_extract_level(g) for g in gigs]
    new_seller_count = sum(1 for l in levels if l in ("", "new seller", "level 1", "level one"))
    if new_seller_count > total * 0.4:
        opportunities.append({
            "signal_type": "low_competition_quality",
            "description": (
                f"{new_seller_count}/{total} gigs are from new or entry-level sellers. "
                f"An experienced seller could dominate this keyword quickly."
            ),
            "confidence": 0.6,
        })

    # --- Signal 4: Few reviews overall (weak incumbents) ---
    review_counts = []
    for gig in gigs:
        rc = gig.get("review_count_cleaned") or gig.get("review_count")
        if isinstance(rc, dict):
            rc = rc.get("cleaned") or rc.get("raw")
        if rc is not None:
            try:
                review_counts.append(int(float(str(rc))))
            except (ValueError, TypeError):
                pass

    if review_counts:
        avg_reviews = sum(review_counts) / len(review_counts)
        if avg_reviews < 50:
            opportunities.append({
                "signal_type": "weak_incumbents",
                "description": (
                    f"Average review count is only {avg_reviews:.0f} — incumbents "
                    f"are not deeply entrenched. A new entrant can catch up fast."
                ),
                "confidence": 0.5,
            })

    # --- Signal 5: Low keyword saturation in titles ---
    kw_tokens = tokenize(keyword) if keyword else set()
    if kw_tokens:
        exact_matches = 0
        for gig in gigs:
            title = _extract_title(gig)
            if keyword.lower() in title.lower():
                exact_matches += 1
        kw_pct = exact_matches / total * 100
        if kw_pct < 50:
            opportunities.append({
                "signal_type": "low_keyword_saturation",
                "description": (
                    f"Only {exact_matches}/{total} gigs ({kw_pct:.0f}%) include "
                    f"'{keyword}' in their title. A well-optimised title could "
                    f"rank above them."
                ),
                "confidence": 0.65,
            })

    # Sort by confidence descending
    opportunities.sort(key=lambda x: x["confidence"], reverse=True)

    return opportunities
