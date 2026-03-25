"""
config/settings.py
──────────────────
Single source of truth for all runtime configuration.
All values can be overridden via environment variables (or .env file).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv

# Load .env file if it exists (no-op if missing)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)


class Settings:
    """Typed configuration container – reads from environment on instantiation."""

    # ── Target ───────────────────────────────────────────────────────────────
    chatbot_url: str
    base_url: str

    # ── Browser ──────────────────────────────────────────────────────────────
    browser: Literal["chrome", "firefox", "edge"]
    headless: bool
    implicit_wait: int
    explicit_wait: int

    # ── Language ─────────────────────────────────────────────────────────────
    test_language: Literal["en", "ar", "both"]

    # ── Mobile ───────────────────────────────────────────────────────────────
    mobile_emulation: bool
    mobile_device: str

    # ── AI Validation ────────────────────────────────────────────────────────
    similarity_threshold: float
    sentence_model: str
    openai_api_key: Optional[str]

    # ── Screenshots / Reporting ───────────────────────────────────────────────
    screenshot_on_failure: bool
    screenshots_dir: Path
    allure_results_dir: Path

    # ── Selenium Grid ────────────────────────────────────────────────────────
    selenium_grid_url: Optional[str]

    # ── Chrome Remote Debugging ───────────────────────────────────────────────
    chrome_debug_port: Optional[int]

    # ── Retry / Rate-limit ───────────────────────────────────────────────────
    max_retries: int
    retry_delay: float
    inter_message_delay: float

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str

    def __init__(self) -> None:
        self.chatbot_url = os.getenv("CHATBOT_URL", "https://beta-ask.u.ae/en/uask")
        self.base_url = os.getenv("BASE_URL", self.chatbot_url)

        self.browser = os.getenv("BROWSER", "chrome").lower()  # type: ignore[assignment]
        self.headless = os.getenv("HEADLESS", "false").lower() == "true"
        self.implicit_wait = int(os.getenv("IMPLICIT_WAIT", "10"))
        self.explicit_wait = int(os.getenv("EXPLICIT_WAIT", "30"))

        self.test_language = os.getenv("TEST_LANGUAGE", "both").lower()  # type: ignore[assignment]

        self.mobile_emulation = os.getenv("MOBILE_EMULATION", "false").lower() == "true"
        self.mobile_device = os.getenv("MOBILE_DEVICE", "iPhone 12")

        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.65"))
        self.sentence_model = os.getenv(
            "SENTENCE_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY") or None

        self.screenshot_on_failure = (
            os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
        )
        self.screenshots_dir = Path(
            os.getenv("SCREENSHOTS_DIR", "reports/screenshots")
        )
        self.allure_results_dir = Path(
            os.getenv("ALLURE_RESULTS_DIR", "reports/allure-results")
        )

        self.selenium_grid_url = os.getenv("SELENIUM_GRID_URL") or None
        _debug_port = os.getenv("CHROME_DEBUG_PORT")
        self.chrome_debug_port = int(_debug_port) if _debug_port else None

        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("RETRY_DELAY", "2.0"))
        self.inter_message_delay = float(os.getenv("INTER_MESSAGE_DELAY", "1.5"))

        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # ── Helpers ──────────────────────────────────────────────────────────────
    def should_run_english(self) -> bool:
        return self.test_language in ("en", "both")

    def should_run_arabic(self) -> bool:
        return self.test_language in ("ar", "both")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Settings(url={self.chatbot_url!r}, browser={self.browser!r}, "
            f"headless={self.headless}, lang={self.test_language!r})"
        )


# Module-level singleton – import this everywhere
settings = Settings()
