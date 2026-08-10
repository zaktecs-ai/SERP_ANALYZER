from __future__ import annotations
"""Additional Tier-1 field extractors for Fiverr SERP gig cards.

Extends parsers.py with fields that go beyond the core identity/price set:
seller country, completed orders, delivery time, badges (Fiverr's Choice /
Pro Verified), response time, and online status.

Each function uses the same _try_selectors(By.CSS_SELECTOR, …) pattern as
parsers.py and returns {raw, normalized, state, selector_used}.
"""

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from typing import Optional

from scraper.selectors import SERP_EXTRA_SELECTORS
from utils.normalization import normalize_text, parse_number


def _try_selectors(element: WebElement, selectors: list,
                   attr: str = None) -> tuple:
    """Try a list of CSS selectors on an element. Returns (text, matched_selector).

    Re-implemented here to avoid circular imports with parsers.py — the logic
    is identical to parsers._try_selectors.
    """
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


def _try_alt_text(element: WebElement, selectors: list) -> tuple:
    """Try selectors, preferring the ``alt`` attribute, falling back to text."""
    for sel in selectors:
        try:
            found = element.find_element(By.CSS_SELECTOR, sel)
            value = found.get_attribute("alt")
            if not value or not value.strip():
                value = found.text
            if value and value.strip():
                return value.strip(), sel
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return None, None


# ---------------------------------------------------------------------------
# Public parsers
# ---------------------------------------------------------------------------

def parse_seller_country(card: WebElement) -> dict:
    """Extract the seller's country from a gig card.

    First attempts to read the ``alt`` attribute of a flag ``<img>`` (e.g.
    "United States"), then falls back to textual location spans.
    """
    selectors = SERP_EXTRA_SELECTORS.get("seller_country", [])
    raw, selector = None, None

    # Phase 1 — flag image alt text
    flag_selectors = [
        "img.flag-icon", "img[alt*='flag']", "img[class*='flag']",
    ]
    for sel in flag_selectors:
        try:
            found = card.find_element(By.CSS_SELECTOR, sel)
            value = found.get_attribute("alt")
            if value and value.strip():
                raw, selector = value.strip(), sel
                break
        except (NoSuchElementException, StaleElementReferenceException):
            continue

    # Phase 2 — textual location spans
    if not raw:
        raw, selector = _try_selectors(card, selectors)

    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_completed_orders(card: WebElement) -> dict:
    """Extract the count of completed orders from a gig card.

    Often rendered as "2.8K orders completed" or "500 orders".  Returns the
    raw text plus a parsed numeric value.
    """
    selectors = SERP_EXTRA_SELECTORS.get("completed_orders", [])
    raw, selector = _try_selectors(card, selectors)

    # Clean up common noise
    cleaned = None
    parsed = None
    if raw:
        import re
        cleaned = re.sub(r"(?i)orders?\s*completed", "", raw)
        cleaned = re.sub(r"(?i)completed\s*orders?", "", cleaned)
        cleaned = cleaned.strip()
        parsed = parse_number(cleaned)

    return {
        "raw": raw,
        "cleaned": cleaned,
        "parsed": int(parsed) if parsed is not None else None,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_delivery_time(card: WebElement) -> dict:
    """Extract the delivery time from a gig card footer.

    Typical text: "2 days delivery", "1 day delivery".  Parses the numeric day
    count and returns both raw text and the parsed integer.
    """
    selectors = SERP_EXTRA_SELECTORS.get("delivery_time", [])
    raw, selector = _try_selectors(card, selectors)

    parsed_days = None
    if raw:
        import re
        match = re.search(r"(\d+)\s*day", raw, re.IGNORECASE)
        if match:
            try:
                parsed_days = int(match.group(1))
            except (ValueError, TypeError):
                pass

    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "parsed_days": parsed_days,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_fiverr_choice(card: WebElement) -> dict:
    """Determine whether the gig card carries a 'Fiverr's Choice' badge.

    Searches for known badge elements and also scans visible badge text for
    the string "fiverr" or "choice".
    """
    selectors = SERP_EXTRA_SELECTORS.get("fiverr_choice", [])
    is_choice = False
    matched_selector = None

    for sel in selectors:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                try:
                    text = el.text.strip().lower()
                    if "fiverr" in text or "choice" in text:
                        is_choice = True
                        matched_selector = sel
                        break
                except StaleElementReferenceException:
                    continue
            if is_choice:
                break
        except (NoSuchElementException, StaleElementReferenceException):
            continue

    # Fallback: scan ALL badge text in the card
    if not is_choice:
        try:
            all_badges = card.find_elements(
                By.CSS_SELECTOR, "span.badge, [class*='badge']"
            )
            for badge in all_badges:
                try:
                    text = badge.text.strip().lower()
                    if "fiverr" in text or "choice" in text:
                        is_choice = True
                        matched_selector = "badge_text_scan"
                        break
                except StaleElementReferenceException:
                    continue
        except Exception:
            pass

    return {
        "raw": is_choice,
        "normalized": is_choice,
        "state": "extracted",
        "selector_used": matched_selector,
    }


def parse_pro_verified(card: WebElement) -> dict:
    """Determine whether the gig card carries a 'Pro Verified' badge.

    Searches known Pro badge selectors and scans visible badge text for
    "pro" or "verified".
    """
    selectors = SERP_EXTRA_SELECTORS.get("pro_verified", [])
    is_pro = False
    matched_selector = None

    for sel in selectors:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                try:
                    text = el.text.strip().lower()
                    if "pro" in text or "verified" in text:
                        is_pro = True
                        matched_selector = sel
                        break
                except StaleElementReferenceException:
                    continue
            if is_pro:
                break
        except (NoSuchElementException, StaleElementReferenceException):
            continue

    # Fallback: scan ALL badge text in the card
    if not is_pro:
        try:
            all_badges = card.find_elements(
                By.CSS_SELECTOR, "span.badge, [class*='badge']"
            )
            for badge in all_badges:
                try:
                    text = badge.text.strip().lower()
                    if "pro" in text or "verified" in text:
                        is_pro = True
                        matched_selector = "badge_text_scan"
                        break
                except StaleElementReferenceException:
                    continue
        except Exception:
            pass

    return {
        "raw": is_pro,
        "normalized": is_pro,
        "state": "extracted",
        "selector_used": matched_selector,
    }


def parse_response_time(card: WebElement) -> dict:
    """Extract the seller's average response time from a gig card.

    Typical text: "2 hour response", "1 hour response".  Parses the numeric
    hour count.
    """
    selectors = SERP_EXTRA_SELECTORS.get("response_time", [])
    raw, selector = _try_selectors(card, selectors)

    parsed_hours = None
    if raw:
        import re
        match = re.search(r"(\d+)\s*hour", raw, re.IGNORECASE)
        if match:
            try:
                parsed_hours = int(match.group(1))
            except (ValueError, TypeError):
                pass

    return {
        "raw": raw,
        "normalized": normalize_text(raw) if raw else None,
        "parsed_hours": parsed_hours,
        "state": "extracted" if raw else "missing",
        "selector_used": selector,
    }


def parse_is_online(card: WebElement) -> dict:
    """Determine whether the seller has a green 'online' indicator on the card.

    Looks for known online-status DOM elements (green dot, online badge) and
    also scans for any element whose class name suggests an online indicator.
    """
    selectors = SERP_EXTRA_SELECTORS.get("is_online", [])
    is_online = False
    matched_selector = None

    for sel in selectors:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, sel)
            if elements:
                is_online = True
                matched_selector = sel
                break
        except (NoSuchElementException, StaleElementReferenceException):
            continue

    # Fallback: look for any element with 'online' in its class name
    if not is_online:
        try:
            candidates = card.find_elements(
                By.CSS_SELECTOR,
                "[class*='online'], [class*='green-dot'], "
                "[class*='Online'], [class*='OnlineStatus']"
            )
            if candidates:
                is_online = True
                matched_selector = "class_scan_online"
        except Exception:
            pass

    return {
        "raw": is_online,
        "normalized": is_online,
        "state": "extracted",
        "selector_used": matched_selector,
    }


def parse_all_extra_fields(card: WebElement) -> dict:
    """Parse all extra Tier-1 fields from a single gig card.

    Returns a flat dict suitable for merging into the core parse_gig_card
    result.
    """
    return {
        "seller_country": parse_seller_country(card),
        "completed_orders": parse_completed_orders(card),
        "delivery_time": parse_delivery_time(card),
        "fiverr_choice": parse_fiverr_choice(card),
        "pro_verified": parse_pro_verified(card),
        "response_time": parse_response_time(card),
        "is_online": parse_is_online(card),
    }
