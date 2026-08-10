"""Competitive intelligence report generator.

Takes the output of competitive_intel analysis functions plus raw gig data
and produces a structured markdown report with actionable recommendations.

The report is suitable for sellers evaluating a keyword before launching or
optimising a gig on Fiverr.
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_get(d: dict, *keys, default=None):
    """Walk nested dict keys; return *default* if any key is missing."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, {})
    return d if d != {} else default


def _slugify(text: str) -> str:
    """Turn a keyword into a safe filename fragment."""
    return re.sub(r"[^a-z0-9_]+", "_", text.lower().strip())[:60]


def _h_bar(value: float, max_value: float, width: int = 20) -> str:
    """Render a text-based horizontal bar for visualising proportions."""
    if max_value <= 0:
        return ""
    filled = min(int(round(value / max_value * width)), width)
    return "█" * filled + "░" * (width - filled)


def _fmt_price(price) -> str:
    """Format a price value for display."""
    if price is None:
        return "N/A"
    return f"${price:,.2f}"


def _fmt_pct(pct) -> str:
    """Format a percentage value."""
    if pct is None:
        return "N/A"
    return f"{pct:.1f}%"


# ---------------------------------------------------------------------------
# Section renderers — each returns a list of markdown lines
# ---------------------------------------------------------------------------

def _render_header(keyword: str) -> list:
    """Render the report title and timestamp."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return [
        f"# Competitive Intelligence Report: *{keyword}*",
        "",
        f"**Generated:** {now}  ",
        "**Source:** Fiverr SERP Analyzer  ",
        "**Confidential — For Internal Planning Only**",
        "",
        "---",
        "",
    ]


def _render_executive_summary(keyword: str, gigs: list,
                               intel: dict) -> list:
    """Render the executive summary with key takeaways."""
    total = len(gigs) if gigs else 0
    lines = [
        "## 1. Executive Summary",
        "",
    ]

    # --- Gig count and price snapshot ---
    prices = []
    ratings = []
    reviews = []
    for g in (gigs or []):
        p = None
        pc = g.get("starting_price_normalized")
        if pc is not None:
            try:
                p = float(str(pc))
            except (ValueError, TypeError):
                pass
        if p is not None and p > 0:
            prices.append(p)

        r = None
        rc = g.get("seller_rating_normalized")
        if rc is not None:
            try:
                r = float(str(rc))
            except (ValueError, TypeError):
                pass
        if r is not None and 0 <= r <= 5:
            ratings.append(r)

        rv = g.get("review_count_cleaned")
        if rv is not None:
            try:
                reviews.append(int(float(str(rv))))
            except (ValueError, TypeError):
                pass

    if total == 0:
        lines.append(
            f"No gigs were collected for **{keyword}**. "
            f"This keyword may be underserved — a first-mover opportunity."
        )
        return lines

    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    avg_reviews = round(sum(reviews) / len(reviews), 1) if reviews else None

    lines.append(
        f"**{total}** gigs analysed for the keyword "
        f"**{keyword}**.  "
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total gigs | {total} |")
    lines.append(f"| Average price | {_fmt_price(avg_price)} |")
    lines.append(f"| Average rating | {avg_rating if avg_rating else 'N/A'} |")
    lines.append(f"| Average reviews | {avg_reviews if avg_reviews else 'N/A'} |")

    # Seller level breakdown
    level_counts = {}
    for g in (gigs or []):
        lvl = _safe_get(g, "seller_level", "normalized")
        if not lvl:
            lvl = g.get("seller_level_normalized", "unknown")
        lvl = str(lvl).strip().lower() or "unknown"
        level_counts[lvl] = level_counts.get(lvl, 0) + 1

    if level_counts:
        lines.append("")
        lines.append("| Seller Level | Count | % |")
        lines.append("|---|---|---|")
        for lvl in sorted(level_counts, key=level_counts.get, reverse=True):
            cnt = level_counts[lvl]
            lines.append(f"| {lvl.title()} | {cnt} | {round(cnt/total*100,1)}% |")

    lines.append("")
    return lines


def _render_pricing(keyword: str, intel: dict) -> list:
    """Render the pricing intelligence section."""
    lines = [
        "## 2. Pricing Intelligence",
        "",
    ]

    pricing_by_level = intel.get("pricing_by_seller_level", {})
    if not pricing_by_level:
        lines.append("No pricing data available.")
        return lines

    lines.append("### Pricing by Seller Level")
    lines.append("")
    lines.append("| Level | Avg Price | Min | Max | Gigs |")
    lines.append("|---|---|---|---|---|")
    for level in sorted(pricing_by_level):
        info = pricing_by_level[level]
        lines.append(
            f"| {level.title()} | {_fmt_price(info['avg_price'])} | "
            f"{_fmt_price(info['min_price'])} | {_fmt_price(info['max_price'])} | "
            f"{info['count']} |"
        )

    lines.append("")

    # Price distribution visual
    all_prices = []
    for info in pricing_by_level.values():
        all_prices.append(info["avg_price"])
    if all_prices:
        max_p = max(all_prices)
        lines.append("### Price Distribution (Average by Level)")
        lines.append("```")
        for level in sorted(pricing_by_level):
            info = pricing_by_level[level]
            bar = _h_bar(info["avg_price"], max_p, width=30)
            lines.append(f"  {level:<16} {_fmt_price(info['avg_price']):>10}  {bar}")
        lines.append("```")
        lines.append("")

    # Strategic takeaways
    lines.append("### Strategic Takeaways")
    lines.append("")

    levels_list = list(pricing_by_level.keys())
    if len(levels_list) >= 2:
        prices_list = [(l, pricing_by_level[l]["avg_price"]) for l in levels_list]
        prices_list.sort(key=lambda x: x[1])
        low_level, low_price = prices_list[0]
        high_level, high_price = prices_list[-1]
        spread = high_price - low_price
        if spread > 0 and low_price > 0:
            lines.append(
                f"- **Price spread:** {_fmt_price(high_price)} ({high_level}) "
                f"vs {_fmt_price(low_price)} ({low_level}) — a "
                f"{round(spread/low_price*100)}% premium for top-tier sellers."
            )

    mid_count = pricing_by_level.get("level 2", {}).get("count", 0)
    top_count = pricing_by_level.get("top rated", {}).get("count", 0)
    pro_count = pricing_by_level.get("pro", {}).get("count", 0)
    if (top_count + pro_count) > 0 and mid_count > 0:
        lines.append(
            f"- **Gap:** {top_count+pro_count} top/pro sellers vs {mid_count} "
            f"mid-level — limited supply at the high end may support "
            f"premium pricing."
        )

    lines.append("")
    return lines


def _render_title_optimization(keyword: str, intel: dict) -> list:
    """Render the title optimisation section."""
    lines = [
        "## 3. Title Optimisation",
        "",
    ]

    word_freq = intel.get("title_word_frequency", [])
    if not word_freq:
        lines.append("No title word frequency data available.")
        return lines

    lines.append("### Top Words in Competitor Titles")
    lines.append("")
    max_count = max(w["count"] for w in word_freq) if word_freq else 1

    lines.append("| Word | Count | % of Gigs | Visual |")
    lines.append("|---|---|---|---|")
    for w in word_freq[:15]:
        bar = _h_bar(w["count"], max_count, width=15)
        lines.append(f"| {w['word']} | {w['count']} | {w['pct']}% | `{bar}` |")
    lines.append("")

    # Recommendations
    lines.append("### Title Recommendations")
    lines.append("")

    saturated = [w for w in word_freq if w["pct"] > 70][:5]
    if saturated:
        words = ", ".join(f"**{w['word']}**" for w in saturated)
        lines.append(
            f"- **Almost every gig uses:** {words}. Include these to avoid "
            f"being filtered out, but they won't differentiate you."
        )

    # Find differentiators — words above median frequency but below 70%
    mid_words = [w for w in word_freq if 30 <= w["pct"] <= 70][:5]
    if mid_words:
        words = ", ".join(f"**{w['word']}**" for w in mid_words)
        lines.append(
            f"- **Differentiators:** {words}. Only some competitors use these "
            f"— they can set your title apart."
        )

    # Rare but present words
    rare = [w for w in word_freq if 0 < w["pct"] <= 15 and w["count"] >= 2][:5]
    if rare:
        words = ", ".join(f"**{w['word']}**" for w in rare)
        lines.append(
            f"- **Underused terms:** {words}. Low saturation — strong "
            f"candidates for niche positioning."
        )

    lines.append("")
    return lines


def _render_feature_gaps(intel: dict) -> list:
    """Render the feature gap matrix section."""
    lines = [
        "## 4. Feature Gaps",
        "",
    ]

    fgm = intel.get("feature_gap_matrix", {})
    if not fgm:
        lines.append(
            "No feature data available (requires Tier-2 gig detail scraping)."
        )
        lines.append("")
        return lines

    lines.append("### Feature Adoption vs. Pricing")
    lines.append("")
    lines.append(
        "| Feature | Adoption | Avg Price When Offered |"
    )
    lines.append("|---|---|---|")

    # Top features by adoption, plus interesting low-adoption/high-price ones
    sorted_features = sorted(
        fgm.items(), key=lambda x: x[1]["present_in_pct"], reverse=True
    )

    for feat, info in sorted_features[:20]:
        lines.append(
            f"| {feat[:50]} | {_fmt_pct(info['present_in_pct'])} | "
            f"{_fmt_price(info['avg_price_when_present'])} |"
        )

    lines.append("")

    # High-value gaps: low adoption, high price
    high_value_gaps = [
        (f, i) for f, i in sorted_features
        if i["present_in_pct"] < 30
        and i.get("avg_price_when_present")
        and i["avg_price_when_present"] > 0
    ]
    if high_value_gaps:
        lines.append("### High-Value Feature Opportunities")
        lines.append("")
        lines.append(
            "These features are offered by **fewer than 30%** of "
            "competitors yet command above-average pricing:"
        )
        lines.append("")
        for feat, info in high_value_gaps[:5]:
            lines.append(
                f"- **{feat}** — only {_fmt_pct(info['present_in_pct'])} "
                f"offer it; avg price {_fmt_price(info['avg_price_when_present'])}"
            )

    lines.append("")
    return lines


def _render_buyer_concerns(intel: dict) -> list:
    """Render the buyer concerns / FAQ / sentiment section."""
    lines = [
        "## 5. Buyer Concerns & FAQ Trends",
        "",
    ]

    # FAQ topics
    faq = intel.get("faq_topic_summary", [])
    if faq:
        lines.append("### Common Buyer Questions")
        lines.append("")
        for topic in faq[:8]:
            lines.append(f"**{topic['topic'].title()}** "
                         f"({topic['mention_count']} mentions)")
            for q in topic.get("example_questions", [])[:2]:
                lines.append(f"- *{q[:120]}*")
            lines.append("")
    else:
        lines.append(
            "No FAQ data available (requires Tier-2 gig detail scraping)."
        )
        lines.append("")

    # Sentiment
    sentiment = intel.get("review_sentiment_analysis", {})
    if sentiment:
        lines.append("### Buyer Sentiment from Reviews")
        lines.append("")

        avg_score = sentiment.get("avg_sentiment_score")
        if avg_score is not None:
            mood = "positive 😊" if avg_score > 0.3 else (
                "neutral 😐" if avg_score >= -0.3 else "negative 😟"
            )
            lines.append(f"**Overall sentiment:** {avg_score:.2f} ({mood})")
            lines.append("")

        praise = sentiment.get("praise_words", [])
        if praise:
            lines.append(
                f"**What buyers love:** "
                f"{', '.join(praise[:10])}"
            )
            lines.append("")

        complaints = sentiment.get("complaint_words", [])
        if complaints:
            lines.append(
                f"**What buyers complain about:** "
                f"{', '.join(complaints[:10])}"
            )
            lines.append("")
    else:
        lines.append(
            "No review sentiment data available "
            "(requires Tier-2 gig detail scraping)."
        )
        lines.append("")

    return lines


def _render_recommendations(keyword: str, gigs: list,
                             intel: dict) -> list:
    """Render actionable recommendations."""
    lines = [
        "## 6. Actionable Recommendations",
        "",
    ]

    opportunities = intel.get("underserved_opportunities", [])
    if not opportunities:
        lines.append(
            f"No clear opportunities detected for **{keyword}**. "
            f"Consider broadening your keyword scope."
        )
        return lines

    lines.append(
        f"Based on analysis of the **{keyword}** SERP, here are the "
        f"highest-confidence opportunities:"
    )
    lines.append("")

    # Top opportunities by confidence
    high_conf = [o for o in opportunities if o["confidence"] >= 0.5][:8]
    medium_conf = [o for o in opportunities if 0.3 <= o["confidence"] < 0.5][:3]

    if high_conf:
        lines.append("### High-Confidence Signals")
        lines.append("")
        for i, opp in enumerate(high_conf, 1):
            icon = "🟢" if opp["confidence"] >= 0.6 else "🟡"
            lines.append(
                f"{i}. {icon} **{opp['signal_type'].replace('_', ' ').title()}** "
                f"(confidence: {opp['confidence']:.0%})  "
            )
            lines.append(f"   {opp['description']}")
            lines.append("")

    if medium_conf:
        lines.append("### Medium-Confidence Signals")
        lines.append("")
        for i, opp in enumerate(medium_conf, 1):
            lines.append(
                f"{i}. 🔵 **{opp['signal_type'].replace('_', ' ').title()}** "
                f"(confidence: {opp['confidence']:.0%})  "
            )
            lines.append(f"   {opp['description']}")
            lines.append("")

    # --- Prescriptive recommendations ---
    lines.append("### Prescriptive Actions")
    lines.append("")

    # Price guidance
    prices = []
    for g in (gigs or []):
        p = None
        pc = g.get("starting_price_normalized")
        if pc is not None:
            try:
                p = float(str(pc))
            except (ValueError, TypeError):
                pass
        if p is not None and p > 0:
            prices.append(p)

    if prices:
        p25 = sorted(prices)[max(0, len(prices) // 4)]
        p50 = sorted(prices)[len(prices) // 2]
        p75 = sorted(prices)[min(len(prices) - 1, 3 * len(prices) // 4)]
        lines.append("#### Pricing Strategy")
        lines.append("")
        lines.append(f"- **Budget entry:** ${p25:.0f} (25th percentile)")
        lines.append(f"- **Mid-market sweet spot:** ${p50:.0f} (median)")
        lines.append(f"- **Premium ceiling:** ${p75:.0f} (75th percentile)")
        lines.append(
            f"- **Recommendation:** Launch at ${p50:.0f}–${p75:.0f} to "
            f"signal quality without pricing yourself out of the market."
        )
        lines.append("")

    # Title guidance
    word_freq = intel.get("title_word_frequency", [])
    if word_freq and keyword:
        kw_words = set(re.findall(r"[a-z0-9]+", keyword.lower()))
        must_have = [
            w["word"] for w in word_freq[:8]
            if w["pct"] > 50 and w["word"] not in kw_words
        ][:3]
        lines.append("#### Title Optimisation")
        lines.append("")
        lines.append(f"- Always include your primary keyword: **{keyword}**")
        if must_have:
            lines.append(
                f"- Include these high-frequency terms: "
                f"{', '.join(must_have)}"
            )
        lines.append(
            "- Add one underused differentiator (see §3 Title Optimisation)"
        )
        lines.append("")

    # FAQ guidance
    faq = intel.get("faq_topic_summary", [])
    if faq:
        top_topics = [t["topic"] for t in faq[:5]]
        lines.append("#### FAQ & Description")
        lines.append("")
        lines.append(
            f"- Address these common buyer questions in your gig description: "
            f"{', '.join(top_topics)}"
        )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"*Report generated by Fiverr SERP Analyzer for keyword: "
        f"**{keyword}**. Re-run weekly to track changes in the competitive "
        f"landscape.*"
    )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_competitive_report(keyword: str, gigs: list,
                                intel_results: dict) -> str:
    """Generate a full competitive intelligence report as a markdown string.

    Args:
        keyword: The search keyword this report analyses.
        gigs: Raw gig data records (Tier 1, Tier 2, or both).
        intel_results: Dict containing the output of one or more functions
            from ``competitive_intel``.  Expected keys::

                title_word_frequency
                pricing_by_seller_level
                feature_gap_matrix
                faq_topic_summary
                review_sentiment_analysis
                underserved_opportunities

    Returns:
        Complete markdown report string.
    """
    lines = []
    lines.extend(_render_header(keyword))
    lines.extend(_render_executive_summary(keyword, gigs, intel_results))
    lines.extend(_render_pricing(keyword, intel_results))
    lines.extend(_render_title_optimization(keyword, intel_results))
    lines.extend(_render_feature_gaps(intel_results))
    lines.extend(_render_buyer_concerns(intel_results))
    lines.extend(_render_recommendations(keyword, gigs, intel_results))

    report = "\n".join(lines)

    # Save to file
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports", "output",
    )
    os.makedirs(output_dir, exist_ok=True)

    safe_kw = _slugify(keyword)
    filename = f"competitive_report_{safe_kw}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Competitive report saved to: {filepath}")

    return report
