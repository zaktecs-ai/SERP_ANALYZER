"""Parsers for extracting data from Fiverr SERP gig cards.

Each parser tries selectors in order and records which one matched.
All parsers tolerate missing nodes — missing data is None, never fabricated.
"""

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from typing import Optional

from scraper.selectors import (
    GIG_TITLE_SELECTORS,
    GIG_URL_SELECTORS,
    GIG_ID_SELECTORS,
    SELLER_NAME_SELECTORS,
    SELLER_PROFILE_URL_SELECTORS,
    SELLER_LEVEL_SELECTORS,
    SELLER_RATING_SELECTORS,
    SELLER_REVIEW_COUNT_SELECTORS,
    STARTING_PRICE_SELECTORS,
    DELIVERY_TIME_SELECTORS,
    BADGES_SELECTORS,
    CATEGORY_SELECTORS,
    SERVICE_TAGS_SELECTORS,
    TOTAL_RESULTS_SELECTORS,
)
from utils.normalization import normalize_text, normalize_url


def _try_selectors(element: WebElement, selectors: list, attr: str = None) -> tuple:
    """Try a list of CSS selectors on an element. Returns (text, matched_selector)."""
    for sel in selectors:
        try:
            found = element.find_element(By.CSS_SELECTOR, sel)
            if attr:
                value = found.get_attribute(attr)
            else:
                value = found.text
            if value and value.strip():
                return value.strip(), sel
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return None, None


def _try_selectors_global(driver, selectors: list, attr: str = None) -> tuple:
    """Try selectors globally on the page. Returns (text, matched_selector)."""
    for sel in selectors:
        try:
            found = driver.find_element(By.CSS_SELECTOR, sel)
            if attr:
                value = found.get_attribute(attr)
            else:
                value = found.text
            if value and value.strip():
                return value.strip(), sel
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return None, None


def parse_gig_title(card: WebElement) -> dict:
    """Extract gig title from a gig card."""
    raw, selector = _try_selectors(card, GIG_TITLE_SELECTORS)
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_gig_url(card: WebElement) -> dict:
    """Extract gig URL from a gig card."""
    raw, selector = _try_selectors(card, GIG_URL_SELECTORS, attr="href")
    return {
        "raw": raw,
        "normalized": normalize_url(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_gig_id(card: WebElement) -> dict:
    """Extract gig ID from a gig card (from data attribute or URL)."""
    raw, selector = _try_selectors(card, GIG_ID_SELECTORS, attr="data-gig-id")
    if not raw:
        raw, selector = _try_selectors(card, GIG_ID_SELECTORS, attr="data-id")
    # Fallback: extract from URL
    if not raw:
        url_data = parse_gig_url(card)
        if url_data["normalized"]:
            import re
            match = re.search(r"/gig/([^/?]+)", url_data["normalized"])
            if match:
                raw = match.group(1)
                selector = "url_regex"
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_seller_name(card: WebElement) -> dict:
    """Extract seller display name from a gig card."""
    raw, selector = _try_selectors(card, SELLER_NAME_SELECTORS)
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_seller_profile_url(card: WebElement) -> dict:
    """Extract seller profile URL from a gig card."""
    raw, selector = _try_selectors(card, SELLER_PROFILE_URL_SELECTORS, attr="href")
    return {
        "raw": raw,
        "normalized": normalize_url(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_seller_level(card: WebElement) -> dict:
    """Extract seller level/status from a gig card."""
    raw, selector = _try_selectors(card, SELLER_LEVEL_SELECTORS)
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_seller_rating(card: WebElement) -> dict:
    """Extract seller rating from a gig card."""
    raw, selector = _try_selectors(card, SELLER_RATING_SELECTORS)
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_review_count(card: WebElement) -> dict:
    """Extract review count from a gig card."""
    raw, selector = _try_selectors(card, SELLER_REVIEW_COUNT_SELECTORS)
    # Clean up common patterns like "(123)" or "123 reviews"
    if raw:
        import re
        cleaned = re.sub(r"[()]", "", raw)
        cleaned = re.sub(r"(?i)reviews?", "", cleaned).strip()
    else:
        cleaned = None
    return {
        "raw": raw,
        "cleaned": cleaned,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_starting_price(card: WebElement) -> dict:
    """Extract starting price from a gig card."""
    raw, selector = _try_selectors(card, STARTING_PRICE_SELECTORS)
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_delivery_time(card: WebElement) -> dict:
    """Extract delivery time from a gig card."""
    raw, selector = _try_selectors(card, DELIVERY_TIME_SELECTORS)
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_badges(card: WebElement) -> dict:
    """Extract badges from a gig card."""
    badges = []
    selector_used = None
    for sel in BADGES_SELECTORS:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, sel)
            if elements:
                selector_used = sel
                for el in elements:
                    text = el.text.strip()
                    if text:
                        badges.append(text)
                break
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return {
        "raw": badges,
        "normalized": [normalize_text(b) for b in badges],
        "state": "extracted" if badges else "missing",
        "selector_used": selector_used,
    }


def parse_category(card: WebElement) -> dict:
    """Extract category from a gig card."""
    raw, selector = _try_selectors(card, CATEGORY_SELECTORS)
    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_service_tags(card: WebElement) -> dict:
    """Extract service tags from a gig card."""
    tags = []
    selector_used = None
    for sel in SERVICE_TAGS_SELECTORS:
        try:
            elements = card.find_elements("css selector", sel)
            if elements:
                selector_used = sel
                for el in elements:
                    text = el.text.strip()
                    if text:
                        tags.append(text)
                break
        except NoSuchElementException:
            continue
    return {
        "raw": tags,
        "normalized": [normalize_text(t) for t in tags],
        "state": "extracted" if tags else "missing",
        "selector_used": selector_used,
    }


def parse_total_results(driver) -> dict:
    """Extract Fiverr's displayed total results count from the SERP."""
    raw, selector = _try_selectors_global(driver, TOTAL_RESULTS_SELECTORS)
    parsed = None
    if raw:
        from utils.normalization import parse_number
        parsed = parse_number(raw)
    return {
        "raw": raw,
        "parsed": int(parsed) if parsed is not None else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_gig_card(card: WebElement) -> dict:
    """Parse all fields from a single gig card.

    Returns a dict with all extracted fields, each carrying raw value,
    normalized value, state, and selector_used.
    """
    return {
        "title": parse_gig_title(card),
        "url": parse_gig_url(card),
        "gig_id": parse_gig_id(card),
        "seller_name": parse_seller_name(card),
        "seller_profile_url": parse_seller_profile_url(card),
        "seller_level": parse_seller_level(card),
        "seller_rating": parse_seller_rating(card),
        "review_count": parse_review_count(card),
        "starting_price": parse_starting_price(card),
        "delivery_time": parse_delivery_time(card),
        "badges": parse_badges(card),
        "category": parse_category(card),
        "service_tags": parse_service_tags(card),
    }