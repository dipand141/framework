"""
utils/screenshot_helper.py
──────────────────────────
Manages screenshot capture, file naming, and Allure attachment.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import allure
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from utils.logger import get_logger

log = get_logger(__name__)


class ScreenshotHelper:
    """Captures screenshots and attaches them to Allure reports."""

    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        self.driver = driver
        self.settings = settings
        self._dir = settings.screenshots_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def capture(self, name: str) -> Path:
        """
        Capture a screenshot, save it to disk, and attach to Allure.
        Returns the path to the saved file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        filename = f"{safe_name}_{timestamp}.png"
        filepath = self._dir / filename

        try:
            self.driver.save_screenshot(str(filepath))
            log.debug("Screenshot saved: %s", filepath)
            self._attach_to_allure(name, filepath)
        except Exception as exc:
            log.error("Failed to capture screenshot '%s': %s", name, exc)

        return filepath

    def capture_on_failure(self, test_name: str) -> Path:
        """Convenience wrapper used in teardown fixtures."""
        return self.capture(f"FAILURE_{test_name}")

    @staticmethod
    def _attach_to_allure(name: str, filepath: Path) -> None:
        try:
            with open(filepath, "rb") as fh:
                allure.attach(
                    fh.read(),
                    name=name,
                    attachment_type=allure.attachment_type.PNG,
                )
        except Exception as exc:
            log.warning("Could not attach screenshot to Allure: %s", exc)
