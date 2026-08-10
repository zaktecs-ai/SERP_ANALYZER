"""Human-paced interaction behaviors for the Fiverr SERP Analyzer.

Provides natural progressive scrolling, gentle mouse movement, and randomized
idle times. These exist for natural pacing, session stability, and lazy-load
correctness in a supervised session. They are NOT a stealth or anti-detection
system.
"""

import random
import time
import math
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    MoveTargetOutOfBoundsException,
)


class HumanPacedInteraction:
    """Manages natural-feeling interaction pacing for attended sessions."""

    def __init__(self, config: dict):
        interaction = config.get("interaction", {})
        self.natural_scroll = interaction.get("natural_scroll", True)
        self.mouse_movement = interaction.get("mouse_movement", True)
        self.idle_probability = interaction.get("idle_probability", 0.2)

    def random_delay(self, min_sec: float, max_sec: float):
        """Sleep for a random duration between min_sec and max_sec."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def progressive_scroll(self, driver, target_count: int = 20,
                           scroll_increment_min: int = 200,
                           scroll_increment_max: int = 500,
                           pause_min: float = 0.5,
                           pause_max: float = 1.5):
        """Scroll the page progressively to trigger lazy-loaded gig cards.

        Scrolls in randomized increments with brief pauses until the target
        number of gig cards are rendered, with occasional small upward
        corrective scrolls.

        Args:
            driver: Selenium WebDriver instance.
            target_count: Number of gig cards to render.
            scroll_increment_min: Minimum scroll pixels per step.
            scroll_increment_max: Maximum scroll pixels per step.
            pause_min: Minimum pause between scrolls.
            pause_max: Maximum pause between scrolls.
        """
        if not self.natural_scroll:
            # Simple scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            return

        from scraper.selectors import GIG_CARD_SELECTORS

        max_scrolls = 30
        scroll_count = 0
        last_card_count = 0
        no_new_cards_count = 0

        while scroll_count < max_scrolls:
            # Count current visible cards
            card_count = 0
            for sel in GIG_CARD_SELECTORS:
                try:
                    cards = driver.find_elements(By.CSS_SELECTOR, sel)
                    if cards:
                        card_count = len(cards)
                        break
                except Exception:
                    continue

            if card_count >= target_count:
                break

            if card_count == last_card_count:
                no_new_cards_count += 1
                if no_new_cards_count >= 5:
                    break
            else:
                no_new_cards_count = 0
                last_card_count = card_count

            # Random scroll increment
            increment = random.randint(scroll_increment_min, scroll_increment_max)

            # Occasionally do a small upward scroll (10% chance)
            if random.random() < 0.1:
                increment = -random.randint(50, 150)

            driver.execute_script(f"window.scrollBy(0, {increment});")

            # Brief pause
            time.sleep(random.uniform(pause_min, pause_max))
            scroll_count += 1

        # Final scroll to ensure all cards are in view
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    def gentle_mouse_move(self, driver):
        """Perform a gentle, curved mouse movement to a neutral page area.

        Movement is small, smooth, and curved. Never produces unintended clicks.
        """
        if not self.mouse_movement:
            return

        try:
            actions = ActionChains(driver)

            # Get viewport size
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")

            # Target a neutral area (center-ish, but offset)
            target_x = viewport_width // 2 + random.randint(-200, 200)
            target_y = viewport_height // 3 + random.randint(-100, 100)

            # Clamp to viewport
            target_x = max(50, min(target_x, viewport_width - 50))
            target_y = max(50, min(target_y, viewport_height - 50))

            # Generate curved path with a few intermediate points
            start_x = random.randint(100, viewport_width - 100)
            start_y = random.randint(100, viewport_height - 100)

            steps = random.randint(3, 6)
            for i in range(1, steps + 1):
                t = i / steps
                # Bezier-like curve with offset
                cx = start_x + (target_x - start_x) * t
                cy = start_y + (target_y - start_y) * t
                # Add sinusoidal offset for curve
                offset = int(30 * math.sin(t * math.pi))
                cx += offset
                cy += offset // 2

                cx = max(0, min(cx, viewport_width))
                cy = max(0, min(cy, viewport_height))

                try:
                    actions.move_by_offset(cx - (start_x if i == 1 else 0),
                                           cy - (start_y if i == 1 else 0))
                    # Reset for subsequent moves
                    if i == 1:
                        start_x, start_y = cx, cy
                except MoveTargetOutOfBoundsException:
                    break

            actions.perform()
            time.sleep(random.uniform(0.1, 0.3))

        except Exception:
            # Mouse movement is non-critical; silently ignore failures
            pass

    def occasional_idle(self):
        """Occasionally pause for a short idle period based on probability."""
        if random.random() < self.idle_probability:
            idle_time = random.uniform(1.0, 3.0)
            time.sleep(idle_time)

    def between_keyword_pause(self, min_sec: float = 8, max_sec: float = 15):
        """Take a longer randomized pause between keywords."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)