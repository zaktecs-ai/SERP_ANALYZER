"""Keyword clustering using lexical similarity (token overlap, stemming).

Groups related keywords (e.g. WEB SCRAPING / DATA EXTRACTION / ECOMMERCE /
PYTHON groups). Uses lexical similarity first; embeddings only if locally
reproducible. Clusters must not merge unrelated services.
"""

import re
from collections import defaultdict
from utils.normalization import tokenize, normalize_title


# Stemming function (simple Porter-like stemmer without external deps)
def _simple_stem(word: str) -> str:
    """Very simple English stemmer for keyword clustering."""
    word = word.lower().strip()
    if len(word) <= 3:
        return word
    # Common suffixes
    if word.endswith("ing"):
        word = word[:-3]
    elif word.endswith("tion"):
        word = word[:-4]
    elif word.endswith("sion"):
        word = word[:-4]
    elif word.endswith("ment"):
        word = word[:-4]
    elif word.endswith("ers"):
        word = word[:-3]
    elif word.endswith("ers"):
        word = word[:-3]
    elif word.endswith("ing"):
        word = word[:-3]
    elif word.endswith("ed"):
        word = word[:-2]
    elif word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def _stem_tokens(tokens: set) -> set:
    """Stem a set of tokens."""
    return {_simple_stem(t) for t in tokens}


def _token_overlap(tokens1: set, tokens2: set) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


def cluster_keywords(keywords: list, threshold: float = 0.3) -> dict:
    """Cluster keywords based on lexical token overlap.

    Args:
        keywords: List of keyword strings.
        threshold: Jaccard similarity threshold for clustering (0-1).

    Returns dict mapping cluster_id -> list of keywords.
    """
    if not keywords:
        return {}

    # Pre-compute stemmed token sets
    kw_tokens = {}
    for kw in keywords:
        tokens = tokenize(kw)
        stemmed = _stem_tokens(tokens)
        kw_tokens[kw] = stemmed

    # Simple greedy clustering
    clusters = {}  # cluster_id -> set of keywords
    cluster_token_sets = {}  # cluster_id -> union of stemmed tokens
    kw_to_cluster = {}  # keyword -> cluster_id
    next_cluster_id = 0

    for kw in keywords:
        if kw in kw_to_cluster:
            continue

        tokens = kw_tokens[kw]
        best_cluster = None
        best_similarity = 0.0

        for cid, c_tokens in cluster_token_sets.items():
            sim = _token_overlap(tokens, c_tokens)
            if sim > best_similarity:
                best_similarity = sim
                best_cluster = cid

        if best_cluster is not None and best_similarity >= threshold:
            # Add to existing cluster
            clusters[best_cluster].add(kw)
            cluster_token_sets[best_cluster] |= tokens
            kw_to_cluster[kw] = best_cluster
        else:
            # Create new cluster
            cid = f"cluster_{next_cluster_id}"
            next_cluster_id += 1
            clusters[cid] = {kw}
            cluster_token_sets[cid] = tokens
            kw_to_cluster[kw] = cid

    # Convert sets to sorted lists
    result = {}
    for cid, kws in clusters.items():
        result[cid] = sorted(kws)

    return result


def name_clusters(clusters: dict) -> dict:
    """Generate human-readable names for clusters based on most common tokens.

    Returns dict mapping cluster_id -> {"name": str, "keywords": list, "size": int}.
    """
    named = {}
    for cid, keywords in clusters.items():
        # Find most common tokens across all keywords in cluster
        token_counts = defaultdict(int)
        for kw in keywords:
            tokens = tokenize(kw)
            for t in tokens:
                token_counts[t] += 1

        # Top 3 tokens as cluster name
        top_tokens = sorted(token_counts, key=token_counts.get, reverse=True)[:3]
        name = " / ".join(top_tokens).upper() if top_tokens else f"Cluster {cid}"

        named[cid] = {
            "name": name,
            "keywords": keywords,
            "size": len(keywords),
        }

    return named


def get_cluster_for_keyword(keyword: str, clusters: dict) -> str:
    """Find which cluster a keyword belongs to."""
    for cid, kws in clusters.items():
        if keyword in kws:
            return cid
    return None