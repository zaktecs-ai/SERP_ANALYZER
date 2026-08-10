"""Text and number normalization utilities."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def normalize_text(text: str) -> str:
    """Normalize whitespace and Unicode (NFC). Returns empty string for None."""
    if text is None:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_url(url: str) -> str:
    """Canonicalize URL: strip tracking params, normalize scheme/host."""
    if not url:
        return ""
    url = url.strip()
    parsed = urlparse(url)
    # Remove tracking/fragment params
    tracking_params = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                       "utm_content", "fbclid", "gclid", "ref", "source",
                       "tracking", "affiliate_id"}
    query_params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in query_params.items()
                if k.lower() not in tracking_params}
    new_query = urlencode(filtered, doseq=True) if filtered else ""
    clean = urlunparse((
        parsed.scheme.lower() if parsed.scheme else "https",
        parsed.netloc.lower(),
        (parsed.path.rstrip("/") or "/").lower(),
        parsed.params,
        new_query,
        ""  # strip fragment
    ))
    return clean


def parse_number(text: str) -> float | None:
    """Parse a number string like '1.2k', '10,000', '4.9' into float.
    Returns None if unparseable.
    """
    if text is None:
        return None
    text = str(text).strip().lower()
    if not text:
        return None

    # Handle k/m suffixes
    multiplier = 1
    if text.endswith("k"):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]

    # Remove commas, currency symbols, spaces
    text = re.sub(r"[,\s$€£¥₹]", "", text)

    try:
        return float(text) * multiplier
    except (ValueError, TypeError):
        return None


def parse_price(text: str) -> float | None:
    """Parse a price string like '$20', '$5.99', '€50' into float.
    Returns None if unparseable.
    """
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    # Remove currency symbols and whitespace
    text = re.sub(r"[$€£¥₹]", "", text).strip()
    text = re.sub(r",", "", text)  # remove thousands separators
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def parse_rating(text: str) -> float | None:
    """Parse a rating string like '4.9', '5.0' into float 0-5.
    Returns None if unparseable.
    """
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    try:
        val = float(text)
        if 0 <= val <= 5:
            return val
        return None
    except (ValueError, TypeError):
        return None


def parse_review_count(text: str) -> int | None:
    """Parse a review count string like '1.2k', '10,000', '245' into int.
    Returns None if unparseable.
    """
    val = parse_number(text)
    if val is not None:
        return int(round(val))
    return None


def normalize_title(text: str) -> str:
    """Normalize a gig title for comparison."""
    text = normalize_text(text)
    text = text.lower()
    return text


def tokenize(text: str) -> set:
    """Tokenize text into a set of lowercase words (alphanumeric only)."""
    if not text:
        return set()
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return set(tokens)


def keyword_token_match(keyword: str, title: str) -> dict:
    """Compute keyword match metrics against a title.

    Returns dict with:
        exact_match: bool (exact keyword in title)
        phrase_match: bool (keyword phrase in title)
        token_matches: int (count of keyword tokens found in title)
        token_match_ratio: float (0-1)
        keyword_position: int or None (0-indexed word position of first match)
    """
    kw_norm = normalize_title(keyword)
    title_norm = normalize_title(title)
    kw_tokens = tokenize(kw_norm)
    title_tokens = tokenize(title_norm)
    title_words = title_norm.split()

    result = {
        "exact_match": kw_norm in title_norm,
        "phrase_match": kw_norm in title_norm,
        "token_matches": len(kw_tokens & title_tokens),
        "token_match_ratio": (len(kw_tokens & title_tokens) / len(kw_tokens)
                              if kw_tokens else 0.0),
        "keyword_position": None,
    }

    # Find position of first keyword token in title words
    for i, word in enumerate(title_words):
        if word in kw_tokens:
            result["keyword_position"] = i
            break

    return result