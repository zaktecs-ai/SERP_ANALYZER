"""Centralized challenge detection for Fiverr SERP scraping.

Detects CAPTCHA pages, "verify you are human" interstitials, unusual-traffic
notices, and block/403-style pages. On detection, pauses automation and alerts
the human operator.
"""

import time
import sys
import platform
from datetime import datetime, timezone

from scraper.selectors import (
    CHALLENGE_TITLE_MARKERS,
    CHALLENGE_DOM_SELECTORS,
    CHALLENGE_BODY_MARKERS,
)
from selenium.common.exceptions import NoSuchElementException


class ChallengeDetector:
    """Detects security challenges and manages attended-mode pauses."""

    def __init__(self, max_challenges: int = 3, col_logger=None, err_logger=None):
        self.max_challenges = max_challenges
        self.challenge_count = 0
        self.col_logger = col_logger
        self.err_logger = err_logger

    def detect(self, driver) -> bool:
        """Check if the current page is a challenge/block page.

        Returns True if a challenge is detected.
        """
        try:
            page_title = driver.title.lower()
        except Exception:
            # If we can't even read the page, assume it might be challenged
            return True

        # Check title markers first (cheap — no DOM round-trip)
        for marker in CHALLENGE_TITLE_MARKERS:
            if marker in page_title:
                return True

        # Check DOM selectors
        for sel in CHALLENGE_DOM_SELECTORS:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    return True
            except NoSuchElementException:
                continue
            except Exception:
                # Other errors (stale element, etc.) — skip this selector
                continue

        # Check body text markers (expensive — fetch page_source only when needed)
        try:
            page_source = driver.page_source.lower()
        except Exception:
            return True

        for marker in CHALLENGE_BODY_MARKERS:
            if marker in page_source:
                return True

        return False

    def handle_challenge(self, driver, keyword: str, url: str) -> bool:
        """Handle a detected challenge: pause, alert, wait for human.

        Returns True if we should continue, False if max challenges exceeded.
        """
        self.challenge_count += 1

        if self.challenge_count > self.max_challenges:
            print("\n" + "=" * 60)
            print("MAX CHALLENGES EXCEEDED — ending run gracefully.")
            print(f"  Challenges encountered: {self.challenge_count}")
            print(f"  Max allowed: {self.max_challenges}")
            print("=" * 60 + "\n")
            return False

        # Terminal bell
        sys.stdout.write("\a\a\a")
        sys.stdout.flush()

        # Show a popup dialog so the user KNOWS to look at the browser
        if platform.system() == "Windows":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "Fiverr showed a security check/CAPTCHA.\n\n"
                    "SOLVE IT IN THE CHROME BROWSER WINDOW:\n"
                    "1. Click the CAPTCHA checkbox / complete the puzzle\n"
                    "2. Wait for Fiverr results to load\n\n"
                    "Then come back here and press ENTER.",
                    "Fiverr SERP Analyzer - CHALLENGE #{} DETECTED".format(self.challenge_count),
                    0x40  # MB_ICONINFORMATION
                )
            except Exception:
                pass
        else:
            # Cross-platform fallback: print a prominent alert banner
            print("\n" + "!" * 60)
            print("!!! Fiverr SERP Analyzer - CHALLENGE #{} DETECTED !!!".format(self.challenge_count))
            print("!" * 60)
            print("  Fiverr showed a security check/CAPTCHA.")
            print("  SOLVE IT IN THE CHROME BROWSER WINDOW:")
            print("  1. Click the CAPTCHA checkbox / complete the puzzle")
            print("  2. Wait for Fiverr results to load")
            print("  Then come back here and press ENTER.")
            print("!" * 60 + "\n")

        # Prominent console banner
        print("\n" + "=" * 60)
        print("==== CHALLENGE DETECTED ====")
        print(f"  Keyword: {keyword}")
        print(f"  URL: {url}")
        print(f"  Challenge #{self.challenge_count} of {self.max_challenges}")
        print(f"  Time: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        print("  >>> LOOK AT THE BROWSER WINDOW <<<")
        print("  Fiverr is showing a security check.")
        print("  Please solve it MANUALLY in the browser window:")
        print("    - Click the CAPTCHA checkbox if present")
        print("    - Complete any puzzle/images if shown")
        print("    - Wait for the page to load normally")
        print("  Then come back here and press ENTER to continue.")
        print("=" * 60)

        # Save a screenshot so the user can see what's on screen even
        # if the Chrome window is hidden behind other windows
        try:
            import os
            import re
            from pathlib import Path
            screenshots_dir = "screenshots"
            Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
            safe_kw = re.sub(r"[^a-zA-Z0-9_-]", "_", keyword)[:50]
            # Use module-level datetime (do NOT re-import inside function - it
            # would shadow the module import and cause UnboundLocalError)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(screenshots_dir, f"challenge_{safe_kw}_{timestamp}.png")
            driver.save_screenshot(screenshot_path)
            print(f"  Screenshot saved to: {screenshot_path}")
            print(f"  Open this file to see the browser screen.")
        except Exception:
            pass

        print("\n" + "=" * 60 + "\n")

        start_wait = time.time()

        try:
            input()  # Wait for ENTER
        except (EOFError, KeyboardInterrupt):
            print("\nInterrupted. Shutting down.")
            return False

        wait_duration = time.time() - start_wait

        # Log the event
        if self.col_logger:
            from utils.logging import log_challenge
            log_challenge(self.col_logger, keyword, url, wait_duration)

        # Re-verify the page is normal
        if self.detect(driver):
            print("\nWARNING: Page still shows challenge after human intervention.")
            print("You may need to navigate manually or refresh.")
            print("Press ENTER to try continuing anyway...")
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                return False

        return True

    def reset(self):
        """Reset challenge counter for a new run."""
        self.challenge_count = 0
