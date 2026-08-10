from __future__ import annotations
"""Tier-2 gig detail page extraction.

Navigates to an individual Fiverr gig URL and extracts deep page data:
full description, pricing packages, tags, FAQ, seller bio, languages,
recent reviews, portfolio info, and video presence.

Returns every field as a dict key — missing data is None, never fabricated.
"""

import time
import re
import math
from datetime import datetime, timezone
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from scraper.selectors import GIG_DETAIL_SELECTORS
from utils.normalization import normalize_text, normalize_url, parse_number


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _try_selectors(element, selectors: list, attr: str = None) -> tuple:
    """Try CSS selectors on an element. Returns (value_or_text, matched_sel)."""
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


def _try_selectors_global(driver: WebDriver, selectors: list,
                          attr: str = None) -> tuple:
    """Try CSS selectors page-wide. Returns (value_or_text, matched_sel)."""
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


def _try_all_elements(element, selectors: list) -> list:
    """Return a list of matching WebElements for a multi-value field."""
    for sel in selectors:
        try:
            found = element.find_elements(By.CSS_SELECTOR, sel)
            if found:
                return found
        except Exception:
            continue
    return []


def _find_section(driver: WebDriver, selectors: list):
    """Find the first element matching one of the section selectors."""
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el:
                return el
        except NoSuchElementException:
            continue
    return None


# ---------------------------------------------------------------------------
# Popup dismissal (best-effort, same strategy as FiverrCollector)
# ---------------------------------------------------------------------------

_POPUP_CLOSE_SELECTORS = [
    "button[aria-label='Close']",
    "button[aria-label='close']",
    "[data-close-button]",
    "button.close",
    "button[class*='close']",
    "a[class*='close']",
    "svg[class*='close']",
    "[class*='modal'] button",
    "[class*='overlay'] button",
    "button[data-dismiss]",
]

_POPUP_BUTTON_TEXTS = [
    "got it", "accept", "accept all", "ok", "okay", "continue",
    "agree", "i agree", "dismiss", "no thanks", "maybe later", "skip",
]


def _dismiss_overlays(driver: WebDriver):
    """Best-effort dismissal of cookie banners, modals, and tooltips."""
    try:
        # Click labelled dismiss buttons
        for text in _POPUP_BUTTON_TEXTS:
            try:
                buttons = driver.find_elements(
                    By.XPATH,
                    (
                        "//button["
                        "  translate(normalize-space(text()),"
                        "  'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                        "  'abcdefghijklmnopqrstuvwxyz') = '{text}'"
                        "] | //a["
                        "  translate(normalize-space(text()),"
                        "  'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                        "  'abcdefghijklmnopqrstuvwxyz') = '{text}'"
                        "] | //span[@role='button']["
                        "  translate(normalize-space(text()),"
                        "  'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                        "  'abcdefghijklmnopqrstuvwxyz') = '{text}'"
                        "]"
                    ).format(text=text)
                )
                for btn in buttons:
                    try:
                        if btn.is_displayed():
                            btn.click()
                            time.sleep(0.3)
                    except Exception:
                        pass
            except Exception:
                pass

        # Click close / X controls
        for sel in _POPUP_CLOSE_SELECTORS:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    try:
                        if el.is_displayed():
                            el.click()
                            time.sleep(0.2)
                    except Exception:
                        pass
            except Exception:
                pass

        # Escape key
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.ESCAPE)
            time.sleep(0.3)
        except Exception:
            pass

    except Exception:
        pass


# ---------------------------------------------------------------------------
# GigPageCollector
# ---------------------------------------------------------------------------

class GigPageCollector:
    """Navigate to a gig detail page and extract Tier-2 data.

    Each field is returned with as much detail as reasonably extractable from
    the page DOM.  Any field that cannot be found is ``None`` (never guessed).
    """

    def __init__(self, browser_manager, config: dict):
        """Initialise with a BrowserManager instance and app config.

        Args:
            browser_manager: A BrowserManager whose ``.start()`` has already
                been called and whose ``.driver`` is ready.
            config: The application config dict (with ``browser.page_timeout``
                etc.).
        """
        self.browser = browser_manager
        self.config = config
        browser_cfg = config.get("browser", {})
        self.page_timeout = browser_cfg.get("page_timeout", 30)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect_gig_detail(self, driver: WebDriver, gig_url: str,
                           keyword: str = "") -> dict:
        """Navigate to *gig_url*, extract all Tier-2 fields, return a dict.

        Args:
            driver: Active Selenium WebDriver.
            gig_url: Fully qualified URL of the gig detail page.
            keyword: The search keyword that surfaced this gig (for tagging).

        Returns:
            dict with keys matching the Tier-2 schema (full_description,
            packages, tags, faq, seller_bio, seller_country, completed_orders,
            languages, recent_reviews, portfolio_count, has_video).
            All values are the extracted data or ``None``.
        """
        result = {
            "keyword": keyword,
            "gig_url": gig_url,
            "collection_timestamp": datetime.now(timezone.utc).isoformat(),
            "full_description": None,
            "packages": [],
            "tags": [],
            "faq": [],
            "seller_bio": None,
            "seller_country": None,
            "completed_orders": None,
            "languages": [],
            "recent_reviews": [],
            "portfolio_count": None,
            "has_video": False,
        }

        try:
            driver.get(gig_url)
        except TimeoutException:
            # Page partially loaded — continue extracting whatever we can
            pass
        except WebDriverException as e:
            result["_load_error"] = str(e)
            return result

        # Let dynamic content settle
        time.sleep(3)

        # Dismiss any cookie / promo overlays
        _dismiss_overlays(driver)

        # Extract fields — each in its own try/except so one failure
        # doesn't prevent the rest from being collected.
        result["full_description"] = self._extract_full_description(driver)
        result["packages"] = self._extract_packages(driver)
        result["tags"] = self._extract_tags(driver)
        result["faq"] = self._extract_faq(driver)
        result["seller_bio"] = self._extract_seller_bio(driver)
        result["seller_country"] = self._extract_seller_country(driver)
        result["completed_orders"] = self._extract_completed_orders(driver)
        result["languages"] = self._extract_languages(driver)
        result["recent_reviews"] = self._extract_recent_reviews(driver)
        result["portfolio_count"] = self._extract_portfolio_count(driver)
        result["has_video"] = self._extract_has_video(driver)

        return result

    # ------------------------------------------------------------------
    # Field extractors
    # ------------------------------------------------------------------

    def _extract_full_description(self, driver: WebDriver) -> Optional[str]:
        """Extract the gig description as raw HTML text."""
        try:
            raw, _ = _try_selectors_global(
                driver, GIG_DETAIL_SELECTORS["full_description"]
            )
            return normalize_text(raw) if raw else None
        except Exception:
            return None

    def _extract_packages(self, driver: WebDriver) -> list:
        """Extract pricing packages (Basic / Standard / Premium).

        Each package dict has: name, price, delivery_days, revisions, features.
        """
        packages = []
        try:
            package_els = _try_all_elements(
                driver, GIG_DETAIL_SELECTORS["packages"]
            )
        except Exception:
            return packages

        if not package_els:
            return packages

        for pkg_el in package_els:
            try:
                name_raw, _ = _try_selectors(
                    pkg_el, GIG_DETAIL_SELECTORS["package_name"]
                )
                price_raw, _ = _try_selectors(
                    pkg_el, GIG_DETAIL_SELECTORS["package_price"]
                )
                delivery_raw, _ = _try_selectors(
                    pkg_el, GIG_DETAIL_SELECTORS["package_delivery"]
                )
                revisions_raw, _ = _try_selectors(
                    pkg_el, GIG_DETAIL_SELECTORS["package_revisions"]
                )

                # Features are a list
                feature_els = _try_all_elements(
                    pkg_el, GIG_DETAIL_SELECTORS["package_features"]
                )
                features = []
                for fe in feature_els:
                    try:
                        ft = fe.text.strip()
                        if ft:
                            features.append(ft)
                    except StaleElementReferenceException:
                        continue

                # Parse delivery days
                delivery_days = None
                if delivery_raw:
                    m = re.search(r"(\d+)", delivery_raw)
                    if m:
                        try:
                            delivery_days = int(m.group(1))
                        except ValueError:
                            pass

                # Parse revisions
                revisions = None
                if revisions_raw:
                    m = re.search(r"(\d+|unlimited)", revisions_raw,
                                  re.IGNORECASE)
                    if m:
                        rev_text = m.group(1).lower()
                        revisions = (rev_text if rev_text == "unlimited"
                                     else int(rev_text))

                # Parse price
                price = None
                if price_raw:
                    price = parse_number(price_raw)

                packages.append({
                    "name": name_raw.strip() if name_raw else None,
                    "price": price,
                    "price_raw": price_raw,
                    "delivery_days": delivery_days,
                    "revisions": revisions,
                    "features": features,
                })
            except Exception:
                continue

        return packages

    def _extract_tags(self, driver: WebDriver) -> list:
        """Extract gig tag/category labels."""
        try:
            tag_els = _try_all_elements(driver, GIG_DETAIL_SELECTORS["tags"])
            tags = []
            seen = set()
            for el in tag_els:
                try:
                    text = el.text.strip()
                    if text and text.lower() not in seen:
                        seen.add(text.lower())
                        tags.append(text)
                except StaleElementReferenceException:
                    continue
            return tags
        except Exception:
            return []

    def _extract_faq(self, driver: WebDriver) -> list:
        """Extract FAQ question/answer pairs.

        Returns a list of dicts with 'question' and 'answer'.
        """
        faq_items = []
        try:
            faq_section = _find_section(
                driver, GIG_DETAIL_SELECTORS["faq_section"]
            )
            if faq_section is None:
                return faq_items

            # Find all FAQ blocks within the section — look for paired
            # question/answer elements.
            question_els = faq_section.find_elements(
                By.CSS_SELECTOR, ", ".join(GIG_DETAIL_SELECTORS["faq_question"])
            )
            answer_els = faq_section.find_elements(
                By.CSS_SELECTOR, ", ".join(GIG_DETAIL_SELECTORS["faq_answer"])
            )

            # Pair by position
            for i, q_el in enumerate(question_els):
                try:
                    question = q_el.text.strip()
                    if not question:
                        continue
                    answer = None
                    if i < len(answer_els):
                        try:
                            answer = answer_els[i].text.strip()
                        except StaleElementReferenceException:
                            pass
                    if question:
                        faq_items.append({
                            "question": question,
                            "answer": answer,
                        })
                except StaleElementReferenceException:
                    continue

        except Exception:
            pass

        return faq_items

    def _extract_seller_bio(self, driver: WebDriver) -> Optional[str]:
        """Extract the seller's about/bio text."""
        try:
            raw, _ = _try_selectors_global(
                driver, GIG_DETAIL_SELECTORS["seller_bio"]
            )
            return normalize_text(raw) if raw else None
        except Exception:
            return None

    def _extract_seller_country(self, driver: WebDriver) -> Optional[str]:
        """Extract the seller's country from the detail page."""
        try:
            raw, _ = _try_selectors_global(
                driver, GIG_DETAIL_SELECTORS["seller_country"]
            )
            return normalize_text(raw) if raw else None
        except Exception:
            return None

    def _extract_completed_orders(self, driver: WebDriver) -> Optional[int]:
        """Extract the count of completed orders from the detail page."""
        try:
            raw, _ = _try_selectors_global(
                driver, GIG_DETAIL_SELECTORS["completed_orders"]
            )
            if raw:
                cleaned = re.sub(r"(?i)orders?\s*(completed)?", "", raw)
                cleaned = re.sub(r"(?i)completed", "", cleaned)
                cleaned = cleaned.strip()
                val = parse_number(cleaned)
                return int(round(val)) if val is not None else None
            return None
        except Exception:
            return None

    def _extract_languages(self, driver: WebDriver) -> list:
        """Extract language proficiencies (e.g. ['English', 'Spanish'])."""
        try:
            lang_els = _try_all_elements(
                driver, GIG_DETAIL_SELECTORS["languages"]
            )
            langs = []
            seen = set()
            for el in lang_els:
                try:
                    text = el.text.strip()
                    # Filter out non-language text — languages are typically
                    # short strings with alphabetic characters
                    if (text and len(text) < 50 and
                            re.search(r"[A-Za-z]", text) and
                            text.lower() not in seen):
                        seen.add(text.lower())
                        langs.append(text)
                except StaleElementReferenceException:
                    continue
            return langs
        except Exception:
            return []

    def _extract_recent_reviews(self, driver: WebDriver) -> list:
        """Extract recent buyer reviews.

        Each review dict: {rating, text, date, buyer_country}.
        Rating is a float 1-5 or None.
        """
        reviews = []
        try:
            review_els = _try_all_elements(
                driver, GIG_DETAIL_SELECTORS["recent_reviews"]
            )
        except Exception:
            return reviews

        for el in review_els:
            try:
                # Rating
                rating_raw, _ = _try_selectors(
                    el, GIG_DETAIL_SELECTORS["review_rating"]
                )
                rating = None
                if rating_raw:
                    m = re.search(r"(\d+(?:\.\d+)?)", rating_raw)
                    if m:
                        try:
                            rating = float(m.group(1))
                        except ValueError:
                            pass

                # Text
                text_raw, _ = _try_selectors(
                    el, GIG_DETAIL_SELECTORS["review_text"]
                )
                text = normalize_text(text_raw) if text_raw else None

                # Date
                date_raw, _ = _try_selectors(
                    el, GIG_DETAIL_SELECTORS["review_date"]
                )
                date = date_raw.strip() if date_raw else None

                # Buyer country
                country_raw, _ = _try_selectors(
                    el, GIG_DETAIL_SELECTORS["review_buyer_country"]
                )
                # Country might be an image alt attribute — try that too
                if not country_raw:
                    try:
                        flag = el.find_element(
                            By.CSS_SELECTOR, "img.flag-icon, img[class*='flag']"
                        )
                        alt = flag.get_attribute("alt")
                        if alt and alt.strip():
                            country_raw = alt.strip()
                    except NoSuchElementException:
                        pass
                country = normalize_text(country_raw) if country_raw else None

                # Only keep reviews that have at least *some* content
                if text or rating:
                    reviews.append({
                        "rating": rating,
                        "text": text,
                        "date": date,
                        "buyer_country": country,
                    })
            except Exception:
                continue

        return reviews

    def _extract_portfolio_count(self, driver: WebDriver) -> Optional[int]:
        """Count the number of portfolio / gallery items."""
        try:
            items = _try_all_elements(
                driver, GIG_DETAIL_SELECTORS["portfolio_count"]
            )
            return len(items) if items else 0
        except Exception:
            return None

    def _extract_has_video(self, driver: WebDriver) -> bool:
        """Check if the gig page includes a video element."""
        try:
            for sel in GIG_DETAIL_SELECTORS["video"]:
                try:
                    els = driver.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False
