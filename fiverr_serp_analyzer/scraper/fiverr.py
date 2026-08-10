"""Fiverr SERP collection orchestration.

Coordinates browser, interaction, challenge detection, and parsers to collect
top-N gig data for a keyword from Fiverr search results.
"""

import time
import random
from datetime import datetime, timezone
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
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


class FiverrCollector:
    """Collects Fiverr SERP data for a list of keywords."""

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

        self.interaction = HumanPacedInteraction(config)
        self.challenge_detector = ChallengeDetector(
            max_challenges=self.max_challenges,
            col_logger=col_logger,
            err_logger=err_logger,
        )

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

        Fiverr loads results dynamically via JavaScript. Waiting for <body>
        is NOT enough — we must wait for the actual gig card elements.
        """
        if timeout is None:
            timeout = self.config.get("browser", {}).get("page_timeout", 30)
        from selenium.webdriver.support.ui import WebDriverWait

        for sel in GIG_CARD_SELECTORS:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                return True
            except TimeoutException:
                continue
        return False

    def _find_gig_cards(self, driver):
        """Find all visible gig cards on the page."""
        for sel in GIG_CARD_SELECTORS:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if cards:
                    return cards, sel
            except Exception:
                continue
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
        return gig_record

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

                # Challenge detection
                if self.challenge_detector.detect(driver):
                    result["challenge_paused"] = True
                    can_continue = self.challenge_detector.handle_challenge(
                        driver, keyword, url
                    )
                    if not can_continue:
                        result["error"] = "max_challenges_exceeded"
                        return result

                # Random delay before interaction
                self.interaction.random_delay(self.delay_min, self.delay_max)

                # WAIT for gig cards to actually render (dynamic JS loading)
                cards_rendered = self._wait_for_gig_cards(driver)
                if not cards_rendered:
                    # Save screenshot + HTML for debugging
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

                # Small settle pause
                time.sleep(random.uniform(1, 2))

                # Optional mouse movement
                self.interaction.gentle_mouse_move(driver)

                # Find gig cards
                cards, card_selector = self._find_gig_cards(driver)
                if not cards:
                    # Save screenshot + HTML for debugging
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

                # If we got some gigs, success
                if result["gigs"]:
                    return result

                # No gigs extracted despite cards found — may need retry
                retries += 1
                if retries <= self.max_retries:
                    print(f"  Retrying ({retries}/{self.max_retries})...")
                    time.sleep(random.uniform(2, 4))
                else:
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