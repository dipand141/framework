"""
pages/base_page.py
──────────────────
Abstract base for all page objects.
Provides driver primitives, waiting helpers, RTL/LTR assertions, and
text normalisation for Arabic / BiDi text.
"""
from __future__ import annotations

import time
import unicodedata
from typing import Optional, Tuple

import allure
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tenacity import retry, stop_after_attempt, wait_fixed

from config.settings import Settings
from utils.logger import get_logger
from utils.screenshot_helper import ScreenshotHelper

Locator = Tuple[str, str]


class BasePage:
    """
    Foundation page object.  All page classes inherit from this.
    Provides interaction primitives, but contains NO test assertions.
    """

    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        self.driver = driver
        self.settings = settings
        self.log = get_logger(self.__class__.__name__)
        self.screenshot = ScreenshotHelper(driver, settings)
        self._wait = WebDriverWait(
            driver,
            timeout=settings.explicit_wait,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    # ── Navigation ─────────────────────────────────────────────────────────────

    def open(self, url: str) -> "BasePage":
        self.log.info("Opening URL: %s", url)
        self.driver.get(url)
        return self

    def get_current_url(self) -> str:
        return self.driver.current_url

    def get_title(self) -> str:
        return self.driver.title

    # ── Waiting ────────────────────────────────────────────────────────────────

    def wait_for_element(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> WebElement:
        wait = (
            WebDriverWait(self.driver, timeout)
            if timeout
            else self._wait
        )
        return wait.until(EC.presence_of_element_located(locator))

    def wait_for_visible(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> WebElement:
        wait = (
            WebDriverWait(self.driver, timeout)
            if timeout
            else self._wait
        )
        return wait.until(EC.visibility_of_element_located(locator))

    def wait_for_clickable(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> WebElement:
        wait = (
            WebDriverWait(self.driver, timeout)
            if timeout
            else self._wait
        )
        return wait.until(EC.element_to_be_clickable(locator))

    def wait_for_text_in_element(
        self,
        locator: Locator,
        text: str,
        timeout: Optional[int] = None,
    ) -> bool:
        wait = (
            WebDriverWait(self.driver, timeout)
            if timeout
            else self._wait
        )
        return wait.until(EC.text_to_be_present_in_element(locator, text))

    def wait_for_element_to_disappear(
        self,
        locator: Locator,
        timeout: Optional[int] = None,
    ) -> bool:
        wait = (
            WebDriverWait(self.driver, timeout)
            if timeout
            else self._wait
        )
        try:
            return wait.until(EC.invisibility_of_element_located(locator))
        except TimeoutException:
            return False

    # ── Interactions ───────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
    )
    def safe_click(self, locator: Locator) -> None:
        element = self.wait_for_clickable(locator)
        element.click()

    def type_text(self, locator: Locator, text: str) -> None:
        element = self.wait_for_visible(locator)
        element.clear()
        element.send_keys(text)

    def get_element_text(self, locator: Locator) -> str:
        element = self.wait_for_visible(locator)
        return element.text

    def get_element_attribute(self, locator: Locator, attribute: str) -> str:
        element = self.wait_for_element(locator)
        return element.get_attribute(attribute) or ""

    def is_element_visible(self, locator: Locator, timeout: int = 5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except (TimeoutException, NoSuchElementException):
            return False

    def is_element_present(self, locator: Locator) -> bool:
        try:
            self.driver.find_element(*locator)
            return True
        except NoSuchElementException:
            return False

    # ── Scrolling ──────────────────────────────────────────────────────────────

    def scroll_to_element(self, locator: Locator) -> None:
        element = self.wait_for_element(locator)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)

    def scroll_to_bottom(self) -> None:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_element_to_bottom(self, locator: Locator) -> None:
        element = self.wait_for_element(locator)
        self.driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight;", element
        )

    # ── Text utilities ─────────────────────────────────────────────────────────

    def get_text_normalized(self, locator: Locator) -> str:
        """
        Extract and normalise text from an element.
        Handles Arabic BiDi control characters and Unicode form differences.
        """
        raw = self.get_element_text(locator)
        return self._normalise_text(raw)

    @staticmethod
    def _normalise_text(text: str) -> str:
        """
        1. NFC-normalise Unicode
        2. Strip BiDi control characters (U+200B, U+200E, U+200F, U+202A–U+202E)
        3. Apply arabic-reshaper + python-bidi if Arabic characters are present
        """
        if not text:
            return ""

        # Unicode NFC
        text = unicodedata.normalize("NFC", text)

        # Strip invisible BiDi / zero-width characters
        bidi_controls = {
            "\u200b", "\u200e", "\u200f",
            "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
            "\u2066", "\u2067", "\u2068", "\u2069",
        }
        text = "".join(ch for ch in text if ch not in bidi_controls)

        # If text contains Arabic characters, reshape + apply BiDi algorithm
        if any("\u0600" <= ch <= "\u06ff" for ch in text):
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display

                text = arabic_reshaper.reshape(text)
                text = get_display(text)
            except ImportError:
                pass  # Libraries not installed – skip reshaping

        return text.strip()

    # ── Layout / Direction ─────────────────────────────────────────────────────

    def get_page_text_direction(self) -> str:
        """Returns 'rtl' or 'ltr' from the html or body element."""
        for selector in ["html", "body"]:
            try:
                el = self.driver.find_element(By.TAG_NAME, selector)
                direction = el.get_attribute("dir") or ""
                if direction.lower() in ("rtl", "ltr"):
                    return direction.lower()
            except NoSuchElementException:
                continue
        # Fall back: check computed style of body
        return self.driver.execute_script(
            "return window.getComputedStyle(document.body).direction;"
        ) or "ltr"

    def get_element_direction(self, locator: Locator) -> str:
        """Returns the text direction of a specific element."""
        element = self.wait_for_element(locator)
        attr_dir = element.get_attribute("dir") or ""
        if attr_dir.lower() in ("rtl", "ltr"):
            return attr_dir.lower()
        # Fallback: computed CSS direction
        return self.driver.execute_script(
            "return window.getComputedStyle(arguments[0]).direction;", element
        ) or "ltr"

    # ── Viewport / Dimension ───────────────────────────────────────────────────

    def get_viewport_width(self) -> int:
        return self.driver.execute_script("return window.innerWidth;")

    def get_viewport_height(self) -> int:
        return self.driver.execute_script("return window.innerHeight;")

    # ── JavaScript helpers ────────────────────────────────────────────────────

    def execute_script(self, script: str, *args):
        return self.driver.execute_script(script, *args)

    def get_element_value(self, locator: Locator) -> str:
        element = self.wait_for_element(locator)
        return element.get_attribute("value") or ""

    # ── Screenshot ────────────────────────────────────────────────────────────

    @allure.step("Take screenshot: {name}")
    def take_screenshot(self, name: str) -> None:
        self.screenshot.capture(name)

    # ── Accessibility (axe-core) ───────────────────────────────────────────────

    def run_accessibility_check(self) -> dict:
        """Run axe-core accessibility audit on the current page."""
        try:
            from axe_selenium_python import Axe

            axe = Axe(self.driver)
            axe.inject()
            results = axe.run()
            return results
        except ImportError:
            self.log.warning("axe-selenium-python not installed – skipping a11y check")
            return {}

    # ── Pause ─────────────────────────────────────────────────────────────────

    def pause(self, seconds: float) -> None:
        time.sleep(seconds)
