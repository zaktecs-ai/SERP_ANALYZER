"""Fiverr SERP collection orchestration.

Coordinates browser, interaction, challenge detection, and parsers to collect
top-N gig data for a keyword from Fiverr search results.
"""

import time
import random
from datetime import datetime, timezone
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)

from scraper.selectors import (
    FIVERR_SEARCH_URL,
    GIG_CARD_SELECTORS,
)
from scraper.parsers import parse_gig_card, parse_total_results
from scraper.challenge import ChallengeDetector
from scraper.interaction import HumanPacedInteraction
from utils.normalization import normalize_url
from scraper.serp_fields import parse_all_extra_fields
from scraper.gig_page import GigPageCollector


class FiverrCollector:
    """Collects Fiverr SERP data for a list of keywords."""

    # Popup/overlay dismissal selectors and button texts
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
        "got it",
        "accept",
        "accept all",
        "ok",
        "okay",
        "continue",
        "agree",
        "i agree",
        "dismiss",
        "no thanks",
        "maybe later",
        "skip",
    ]

    def __init__(self, browser_manager, config: dict,
                 col_logger=None, err_logger=None):
        self.browser = browser_manager
        self.config = config
        self.col_logger = col_logger
        self.err_logger = err_logger

        collection = config.get("collection", {})
        self.top_n = collection.get("top_n", 20)
        self.delay_min = collection.get("delay_min", 3)
        self.delay_max = collection.get("delay_max", 7)
        self.keyword_pause_min = collection.get("keyword_pause_min", 8)
        self.keyword_pause_max = collection.get("keyword_pause_max", 15)
        self.max_retries = collection.get("max_retries", 2)
        self.max_challenges = collection.get("max_challenges_per_run", 3)
        self.collect_details = collection.get("collect_gig_details", False)
        self.max_detail_pages = min(collection.get("max_detail_pages", 10), self.top_n)
        self.detail_delay_min = collection.get("detail_delay_min", 4)
        self.detail_delay_max = collection.get("detail_delay_max", 8)
        if self.collect_details:
            self.gig_page_collector = GigPageCollector(browser_manager, config, col_logger=col_logger, err_logger=err_logger)
        else:
            self.gig_page_collector = None

        self.interaction = HumanPacedInteraction(config)
        self.challenge_detector = ChallengeDetector(
            max_challenges=self.max_challenges,
            col_logger=col_logger,
            err_logger=err_logger,
        )

    # ------------------------------------------------------------------
    # Popup / overlay dismissal
    # ------------------------------------------------------------------

    def _dismiss_popups(self, driver):
        """Aggressively dismiss Fiverr overlays, tooltips, and modals.

        Fiverr frequently shows a "Got it" tooltip for new features
        (e.g. "Hourly rates filter [New]") that blocks scraping.
        This method tries MULTIPLE approaches to dismiss it.
        """
        # Give the popup time to render before attempting to dismiss
        time.sleep(2)

        # Approach 1: "Got it" button via XPATH — most common Fiverr popup
        try:
            btns = driver.find_elements(By.XPATH,
                "//button[contains(translate(text(), "
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                "'abcdefghijklmnopqrstuvwxyz'), 'got it')]")
            for b in btns:
                try:
                    if b.is_displayed():
                        b.click()
                        time.sleep(0.5)
                except Exception:
                    pass
        except Exception:
            pass

        # Approach 3: Click ALL visible buttons with known dismiss texts
        for text in self._POPUP_BUTTON_TEXTS:
            try:
                btns = driver.find_elements(By.XPATH,
                    f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]")
                for b in btns:
                    try:
                        if b.is_displayed():
                            b.click()
                            time.sleep(0.2)
                    except Exception:
                        pass
            except Exception:
                pass

        # Approach 4: CSS close selectors
        for sel in self._POPUP_CLOSE_SELECTORS:
            try:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    try:
                        if el.is_displayed():
                            el.click()
                            time.sleep(0.2)
                    except Exception:
                        pass
            except Exception:
                pass

        # Approach 5: Escape key
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.3)
        except Exception:
            pass

        # Approach 6: Click anywhere outside popup on body
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            webdriver.ActionChains(driver).move_to_element_with_offset(body, 10, 10).click().perform()
            time.sleep(0.3)
        except Exception:
            pass

    def _build_search_url(self, keyword: str) -> str:
        """Build the Fiverr search URL for a keyword."""
        encoded = quote_plus(keyword)
        return FIVERR_SEARCH_URL.format(query=encoded)

    def _wait_for_page_load(self, driver, timeout: int = None):
        """Wait for the page to fully load."""
        if timeout is None:
            timeout = self.config.get("browser", {}).get("page_timeout", 30)
        try:
            # Wait for body to be present
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # Extra settle time for dynamic content
        except TimeoutException:
            pass

    def _wait_for_gig_cards(self, driver, timeout: int = None):
        """Wait for gig cards to actually render on the page.

        Fiverr loads results dynamically via React. Waiting for <body> or even
        ``presence_of_element_located`` on a card selector is NOT enough —
        React may have created empty DOM shells whose content hasn't populated
        yet.

        This method waits for at least one card to be present AND contain
        visible text, confirming that React has finished hydrating the cards.
        """
        if timeout is None:
            timeout = self.config.get("browser", {}).get("page_timeout", 30)
        from selenium.webdriver.support.ui import WebDriverWait

        deadline = time.time() + timeout

        for sel in GIG_CARD_SELECTORS:
            try:
                # Phase 1 — wait for any matching element to appear in the DOM
                WebDriverWait(driver, max(1, deadline - time.time())).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )

                # Phase 2 — poll until at least one card has populated text
                # (React renders shells first, then hydrates content)
                while time.time() < deadline:
                    cards = driver.find_elements(By.CSS_SELECTOR, sel)
                    for card in cards:
                        try:
                            text = card.text.strip()
                            if text and len(text) > 10:
                                return True
                        except StaleElementReferenceException:
                            continue
                    time.sleep(0.5)

                # Timed out — cards present but never got text content
                return False

            except TimeoutException:
                continue

        return False

    def _find_gig_cards(self, driver):
        """Find all visible gig cards on the page.

        Tries the configured CSS selectors first, then falls back to a more
        robust strategy: find any ``<a href*='/gig/'>`` links and climb to
        their nearest card-like container.  This catches cards whose outer
        wrapper class has changed between Fiverr deployments.
        """
        # --- Strategy 1: known CSS selectors -----------------------------
        for sel in GIG_CARD_SELECTORS:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if cards:
                    return cards, sel
            except Exception:
                continue

        # --- Strategy 2: find gig links, climb to card containers --------
        try:
            gig_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/gig/']")
            if gig_links:
                cards = []
                seen = set()
                for link in gig_links:
                    try:
                        # Climb up to find the nearest card-like wrapper
                        parent = link
                        card_container = link
                        for _ in range(6):
                            try:
                                parent = parent.find_element(By.XPATH, "..")
                            except Exception:
                                break
                            cls = (parent.get_attribute("class") or "").lower()
                            if any(pat in cls for pat in (
                                "gig-card", "gig-wrapper", "basic-gig",
                                "gig-card-layout",
                            )):
                                card_container = parent
                                break
                            # Also accept any div/article/li with a meaningful class
                            tag = parent.tag_name.lower()
                            if tag in ("div", "article", "li") and cls:
                                card_container = parent
                                break
                        elem_id = card_container.id if (hasattr(card_container, 'id') and card_container.id) else id(card_container)
                        if elem_id not in seen:
                            seen.add(elem_id)
                            cards.append(card_container)
                    except Exception:
                        continue

                if cards:
                    return cards, "a[href*='/gig/'] (climbed to container)"
        except Exception:
            pass

        return [], None

    def _extract_gig_data(self, card, keyword: str, position: int) -> dict:
        """Extract all fields from a single gig card."""
        try:
            parsed = parse_gig_card(card)
        except Exception as e:
            if self.err_logger:
                from utils.logging import log_error
                log_error(self.err_logger, keyword, "parse_failure",
                          f"pos={position}: {str(e)}")
            return None

        # Build the raw gig record
        gig_record = {
            "keyword": keyword,
            "serp_position": position,
            "collection_timestamp": datetime.now(timezone.utc).isoformat(),
            "title_raw": parsed["title"]["raw"],
            "title_normalized": parsed["title"]["normalized"],
            "title_state": parsed["title"]["state"],
            "title_selector": parsed["title"]["selector_used"],
            "url_raw": parsed["url"]["raw"],
            "url_normalized": parsed["url"]["normalized"],
            "url_state": parsed["url"]["state"],
            "url_selector": parsed["url"]["selector_used"],
            "gig_id_raw": parsed["gig_id"]["raw"],
            "gig_id_normalized": parsed["gig_id"]["normalized"],
            "gig_id_state": parsed["gig_id"]["state"],
            "gig_id_selector": parsed["gig_id"]["selector_used"],
            "seller_name_raw": parsed["seller_name"]["raw"],
            "seller_name_normalized": parsed["seller_name"]["normalized"],
            "seller_name_state": parsed["seller_name"]["state"],
            "seller_name_selector": parsed["seller_name"]["selector_used"],
            "seller_profile_url_raw": parsed["seller_profile_url"]["raw"],
            "seller_profile_url_normalized": parsed["seller_profile_url"]["normalized"],
            "seller_profile_url_state": parsed["seller_profile_url"]["state"],
            "seller_profile_url_selector": parsed["seller_profile_url"]["selector_used"],
            "seller_level_raw": parsed["seller_level"]["raw"],
            "seller_level_normalized": parsed["seller_level"]["normalized"],
            "seller_level_state": parsed["seller_level"]["state"],
            "seller_level_selector": parsed["seller_level"]["selector_used"],
            "seller_rating_raw": parsed["seller_rating"]["raw"],
            "seller_rating_normalized": parsed["seller_rating"]["normalized"],
            "seller_rating_state": parsed["seller_rating"]["state"],
            "seller_rating_selector": parsed["seller_rating"]["selector_used"],
            "review_count_raw": parsed["review_count"]["raw"],
            "review_count_cleaned": parsed["review_count"]["cleaned"],
            "review_count_state": parsed["review_count"]["state"],
            "review_count_selector": parsed["review_count"]["selector_used"],
            "starting_price_raw": parsed["starting_price"]["raw"],
            "starting_price_normalized": parsed["starting_price"]["normalized"],
            "starting_price_state": parsed["starting_price"]["state"],
            "starting_price_selector": parsed["starting_price"]["selector_used"],
            "delivery_time_raw": parsed["delivery_time"]["raw"],
            "delivery_time_normalized": parsed["delivery_time"]["normalized"],
            "delivery_time_state": parsed["delivery_time"]["state"],
            "delivery_time_selector": parsed["delivery_time"]["selector_used"],
            "badges_raw": parsed["badges"]["raw"],
            "badges_normalized": parsed["badges"]["normalized"],
            "badges_state": parsed["badges"]["state"],
            "badges_selector": parsed["badges"]["selector_used"],
            "category_raw": parsed["category"]["raw"],
            "category_normalized": parsed["category"]["normalized"],
            "category_state": parsed["category"]["state"],
            "category_selector": parsed["category"]["selector_used"],
            "service_tags_raw": parsed["service_tags"]["raw"],
            "service_tags_normalized": parsed["service_tags"]["normalized"],
            "service_tags_state": parsed["service_tags"]["state"],
            "service_tags_selector": parsed["service_tags"]["selector_used"],
        }

        # Add Tier 1 extra fields (country, orders, badges, etc.)
        try:
            extra_fields = parse_all_extra_fields(card)
            gig_record.update(extra_fields)
        except Exception:
            pass

        return gig_record

    def _log_page_state(self, driver, keyword: str, context: str):
        """Print page title + visible body text snippet for debugging."""
        try:
            title = driver.title
            body_el = driver.find_element(By.TAG_NAME, "body")
            body_text = body_el.text[:800] if body_el else "(no body)"
            print(f"\n  [{context}] keyword='{keyword}'")
            print(f"  Page title: {title}")
            print(f"  Body snippet (first 800 chars):\n{body_text}\n")
        except Exception:
            print(f"\n  [{context}] keyword='{keyword}' — could not read page state")

    def collect_keyword(self, keyword: str) -> dict:
        """Collect SERP data for a single keyword.

        Returns a dict with:
            keyword, url, total_results, gigs (list), error (str or None),
            challenge_paused (bool), timestamp
        """
        driver = self.browser.get_driver()
        url = self._build_search_url(keyword)

        result = {
            "keyword": keyword,
            "url": url,
            "total_results_raw": None,
            "total_results_parsed": None,
            "total_results_state": "missing",
            "gigs": [],
            "error": None,
            "challenge_paused": False,
            "collection_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        retries = 0
        while retries <= self.max_retries:
            try:
                # Navigate to search URL
                driver.get(url)
                self._wait_for_page_load(driver)

                # --- Dismiss popups after navigation ---
                self._dismiss_popups(driver)

                # Challenge detection
                if self.challenge_detector.detect(driver):
                    result["challenge_paused"] = True
                    can_continue = self.challenge_detector.handle_challenge(
                        driver, keyword, url
                    )
                    if not can_continue:
                        result["error"] = "max_challenges_exceeded"
                        return result

                    # --- Dismiss popups that may appear after challenge solve ---
                    self._dismiss_popups(driver)

                # Random delay before interaction
                self.interaction.random_delay(self.delay_min, self.delay_max)

                # WAIT for gig cards to actually render (dynamic JS loading)
                cards_rendered = self._wait_for_gig_cards(driver)
                if not cards_rendered:
                    self._log_page_state(driver, keyword, "no_gig_cards_rendered")
                    self.browser.save_screenshot(keyword)
                    self.browser.save_html(keyword)
                    result["error"] = "no_gig_cards_found"
                    if self.err_logger:
                        from utils.logging import log_error
                        log_error(self.err_logger, keyword, "no_gig_cards",
                                  "Gig cards never rendered after wait")
                    return result

                # Extract total results count
                total_data = parse_total_results(driver)
                result["total_results_raw"] = total_data["raw"]
                result["total_results_parsed"] = total_data["parsed"]
                result["total_results_state"] = total_data["state"]
                result["total_results_selector"] = total_data["selector_used"]

                # Scroll to load more gig cards
                self.interaction.progressive_scroll(driver, target_count=self.top_n)

                # --- Dismiss any popups that appeared during scroll ---
                self._dismiss_popups(driver)

                # Longer settle pause for lazy-loaded images / cards to fully
                # render (was 1-2 s, which is too short for React hydration)
                time.sleep(3)

                # Optional mouse movement
                self.interaction.gentle_mouse_move(driver)

                # Find gig cards
                cards, card_selector = self._find_gig_cards(driver)
                if not cards:
                    self._log_page_state(driver, keyword, "no_gig_cards_matched")
                    self.browser.save_screenshot(keyword)
                    self.browser.save_html(keyword)
                    result["error"] = "no_gig_cards_found"
                    if self.err_logger:
                        from utils.logging import log_error
                        log_error(self.err_logger, keyword, "no_gig_cards",
                                  "No gig cards matched any selector")
                    return result

                # Extract data from each card, deduplicating by URL
                seen_urls = set()
                position = 0
                for card in cards:
                    if len(result["gigs"]) >= self.top_n:
                        break

                    try:
                        gig_data = self._extract_gig_data(card, keyword, position + 1)
                        if gig_data is None:
                            continue

                        # Deduplicate by normalized URL
                        norm_url = gig_data.get("url_normalized", "")
                        if norm_url and norm_url in seen_urls:
                            continue
                        if norm_url:
                            seen_urls.add(norm_url)

                        position += 1
                        gig_data["serp_position"] = position
                        gig_data["card_selector_used"] = card_selector
                        result["gigs"].append(gig_data)

                        # Log collection
                        if self.col_logger:
                            from utils.logging import log_collection
                            log_collection(
                                self.col_logger, keyword, url, position,
                                f"extracted: {gig_data.get('title_normalized', 'N/A')[:60]}"
                            )

                    except StaleElementReferenceException:
                        if self.err_logger:
                            from utils.logging import log_error
                            log_error(self.err_logger, keyword, "stale_element",
                                      f"pos={position}")
                        continue
                    except Exception as e:
                        if self.err_logger:
                            from utils.logging import log_error
                            log_error(self.err_logger, keyword, "card_extraction_error",
                                      f"pos={position}: {str(e)}")
                        continue

                # --- Tier 2: Gig detail page scraping (if enabled) ---
                if self.collect_details and self.gig_page_collector is not None and result["gigs"]:
                    print(f"  Scraping {min(len(result['gigs']), self.max_detail_pages)} gig detail pages...", end=" ", flush=True)
                    detail_count = 0
                    for gig in result["gigs"][:self.max_detail_pages]:
                        try:
                            gig_url = gig.get("url_normalized")
                            if not gig_url:
                                continue
                            detail = self.gig_page_collector.collect_gig_detail(
                                driver, gig_url, keyword
                            )
                            if detail and not detail.get("error"):
                                gig.update(detail)
                                detail_count += 1
                            # Random delay between detail pages
                            time.sleep(random.uniform(self.detail_delay_min, self.detail_delay_max))
                        except Exception as e:
                            if self.err_logger:
                                from utils.logging import log_error
                                log_error(self.err_logger, keyword, "detail_page_error", str(e)[:200])
                    print(f"done ({detail_count} pages scraped)")

                # If we got some gigs, success
                if result["gigs"]:
                    return result

                # No gigs extracted despite cards found — may need retry
                retries += 1
                if retries <= self.max_retries:
                    print(f"  Retrying ({retries}/{self.max_retries})...")
                    time.sleep(random.uniform(2, 4))
                else:
                    self._log_page_state(driver, keyword, "extraction_returned_no_gigs")
                    result["error"] = "extraction_returned_no_gigs"
                    return result

            except TimeoutException:
                retries += 1
                if retries <= self.max_retries:
                    print(f"  Timeout — retrying ({retries}/{self.max_retries})...")
                    time.sleep(random.uniform(2, 4))
                else:
                    self.browser.save_screenshot(keyword)
                    self.browser.save_html(keyword)
                    result["error"] = "timeout"
                    if self.err_logger:
                        from utils.logging import log_error
                        log_error(self.err_logger, keyword, "timeout",
                                  f"after {self.max_retries} retries")
                    return result

            except WebDriverException as e:
                retries += 1
                if retries <= self.max_retries:
                    print(f"  Browser error — restarting ({retries}/{self.max_retries})...")
                    try:
                        self.browser.restart()
                        driver = self.browser.get_driver()
                    except Exception:
                        pass
                    time.sleep(random.uniform(2, 4))
                else:
                    result["error"] = f"browser_error: {str(e)[:200]}"
                    if self.err_logger:
                        from utils.logging import log_error
                        log_error(self.err_logger, keyword, "browser_error",
                                  str(e)[:200])
                    return result

            except Exception as e:
                retries += 1
                if retries <= self.max_retries:
                    print(f"  Error — retrying ({retries}/{self.max_retries}): {str(e)[:100]}")
                    time.sleep(random.uniform(2, 4))
                else:
                    self.browser.save_screenshot(keyword)
                    self.browser.save_html(keyword)
                    result["error"] = f"unexpected: {str(e)[:200]}"
                    if self.err_logger:
                        from utils.logging import log_error
                        log_error(self.err_logger, keyword, "unexpected_error",
                                  str(e)[:200])
                    return result

        return result

    def reset_challenges(self):
        """Reset challenge counter for a fresh run."""
        self.challenge_detector.reset()