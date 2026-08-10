"""Browser management for the Fiverr SERP Analyzer.

Uses undetected-chromedriver for a more natural browser fingerprint.
Headed mode is enforced — headless is prohibited (constraint C1).
No proxy configuration (constraint C2).
"""

import sys
import os
import time
import uuid
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException


class BrowserManager:
    """Manages a single headed Chrome browser session."""

    def __init__(self, config: dict):
        browser_config = config.get("browser", {})
        self.headless = browser_config.get("headless", False)
        self.page_timeout = browser_config.get("page_timeout", 30)
        self.driver = None
        self.wait = None

        # Enforce headed mode (constraint C1)
        if self.headless:
            print("ERROR: headless mode is prohibited by constraint C1.")
            print("The browser MUST run headed (visible window) at all times.")
            print("Set browser.headless: false in config.yaml and restart.")
            sys.exit(1)

    def start(self):
        """Launch a headed Chrome browser session using undetected-chromedriver."""
        try:
            import undetected_chromedriver as uc
        except ImportError:
            print("ERROR: undetected-chromedriver not installed.")
            print("Run: pip install undetected-chromedriver")
            sys.exit(1)

        # Use a FRESH Chrome profile - guarantees a new visible window
        # even if Chrome is already running on this system.
        # Use a unique profile dir per run to avoid stale lock file issues.
        profile_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "chrome_profile",
            str(uuid.uuid4())[:8],
        )
        os.makedirs(profile_dir, exist_ok=True)

        # MINIMIZE THE CONSOLE WINDOW so Chrome is the ONLY visible window.
        # This guarantees the user sees the Chrome browser.
        try:
            import ctypes
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
        except Exception:
            pass

        try:
            print("Starting Chrome browser (undetected mode)...")

            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--window-size=1280,900")
            options.add_argument("--window-position=0,0")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-popup-blocking")

            # No proxy (constraint C2)
            options.add_argument("--no-proxy-server")

            # User agent — standard Chrome
            options.add_argument(
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

            self.driver = uc.Chrome(
                options=options,
                user_data_dir=profile_dir,
                headless=False,
                version_main=None,
            )
            self.driver.set_page_load_timeout(self.page_timeout)
            self.wait = WebDriverWait(self.driver, self.page_timeout)

            # Switch to the Chrome window and bring to front
            window_handle = self.driver.current_window_handle
            self.driver.switch_to.window(window_handle)

            # Print window title for debugging
            try:
                print(f"Chrome window title: '{self.driver.title}'")
                print(f"Window handles: {self.driver.window_handles}")
            except Exception:
                pass

            # FORCE the window to be visible AND on top of everything
            self._force_visible_topmost()

            try:
                self.driver.set_window_position(0, 0)
            except Exception:
                pass

            try:
                self.driver.execute_script("window.focus();")
            except Exception:
                pass

            self._bring_to_front()

            print(f"Browser started (headed, page_timeout={self.page_timeout}s)")
            print(">>> Chrome window is now OPEN and ON TOP - look at your screen now <<<")
            print(">>> (A window showing Fiverr should be covering your screen) <<<")
            return self.driver
        except WebDriverException as e:
            print(f"ERROR: Failed to start browser: {e}")
            print("Ensure Chrome/Chromium is installed and accessible.")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Could not launch Chrome driver: {e}")
            print("This may be a driver download issue (network).")
            print("Try: pip install --upgrade undetected-chromedriver")
            sys.exit(1)

    def _force_visible_topmost(self):
        """Force the Chrome window to be visible AND always-on-top using SetWindowPos."""
        try:
            import ctypes

            user32 = ctypes.windll.user32
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_SHOWWINDOW = 0x0040

            hwnd = self._find_chrome_window()
            if hwnd:
                user32.ShowWindow(hwnd, 5)  # SW_SHOW
                user32.SetWindowPos(
                    hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
                time.sleep(2)
                HWND_NOTOPMOST = -2
                user32.SetWindowPos(
                    hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
                )
                user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _bring_to_front(self):
        """Bring the Chrome browser window to the foreground using Windows API."""
        try:
            import ctypes
            import time

            user32 = ctypes.windll.user32
            user32.FlashWindow(user32.GetForegroundWindow(), True)

            hwnd = self._find_chrome_window()
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                time.sleep(0.5)
        except Exception:
            pass

    def _find_chrome_window(self):
        """Find the Chrome window handle using EnumWindows."""
        try:
            import ctypes

            user32 = ctypes.windll.user32
            CHROME_CLASS = "Chrome_WidgetWin_1"
            result = []

            enum_proc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )

            @enum_proc
            def callback(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    class_buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(hwnd, class_buf, 256)
                    class_name = class_buf.value
                    if class_name == CHROME_CLASS:
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            result.append(hwnd)
                return True

            user32.EnumWindows(callback, 0)
            return result[0] if result else None
        except Exception:
            return None

    def get_driver(self):
        """Return the current WebDriver instance."""
        if self.driver is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.driver

    def get_wait(self):
        """Return the WebDriverWait instance."""
        if self.wait is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self.wait

    def restart(self):
        """Restart the browser after a crash."""
        print("Restarting browser...")
        self.shutdown()
        return self.start()

    def shutdown(self):
        """Cleanly shut down the browser."""
        if self.driver:
            try:
                self.driver.quit()
                print("Browser shut down.")
            except Exception as e:
                print(f"Warning: Error during browser shutdown: {e}")
            finally:
                self.driver = None
                self.wait = None

    def save_screenshot(self, keyword: str, screenshots_dir: str = "screenshots"):
        """Save a screenshot of the current page."""
        if not self.driver:
            return None
        Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
        import re
        from datetime import datetime
        safe_kw = re.sub(r"[^a-zA-Z0-9_-]", "_", keyword)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_kw}_{timestamp}.png"
        filepath = os.path.join(screenshots_dir, filename)
        try:
            self.driver.save_screenshot(filepath)
            return filepath
        except Exception as e:
            print(f"Warning: Failed to save screenshot: {e}")
            return None

    def save_html(self, keyword: str, html_dir: str = "data/html_failures"):
        """Save the current page HTML source."""
        if not self.driver:
            return None
        Path(html_dir).mkdir(parents=True, exist_ok=True)
        import re
        from datetime import datetime
        safe_kw = re.sub(r"[^a-zA-Z0-9_-]", "_", keyword)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_kw}_{timestamp}.html"
        filepath = os.path.join(html_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            return filepath
        except Exception as e:
            print(f"Warning: Failed to save HTML: {e}")
            return None