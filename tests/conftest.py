"""
tests/conftest.py
─────────────────
Fixture orchestration hub for the U-Ask QA framework.

Fixture dependency graph:
  settings (session)
    ├── test_data   (session)
    ├── ai_validator (session)
    └── driver      (function)
            └── chatbot_page (function)
                      └── [all test functions]

Hooks:
  pytest_configure       – writes Allure environment.properties
  pytest_runtest_makereport – stores per-phase pass/fail for teardown screenshot
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Generator

import allure
import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings, settings as _global_settings
from pages.chatbot_page import ChatbotPage
from utils.ai_validator import AIValidator
from utils.driver_factory import DriverFactory
from utils.logger import get_logger
from utils.screenshot_helper import ScreenshotHelper

log = get_logger("conftest")

# ── Allure environment.properties ────────────────────────────────────────────


def pytest_configure(config: pytest.Config) -> None:
    """Write Allure environment metadata once per session."""
    results_dir = Path(_global_settings.allure_results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    env_file = results_dir / "environment.properties"
    env_content = "\n".join(
        [
            f"Browser={_global_settings.browser}",
            f"ChatbotURL={_global_settings.chatbot_url}",
            f"Headless={_global_settings.headless}",
            f"Language={_global_settings.test_language}",
            f"SimilarityThreshold={_global_settings.similarity_threshold}",
            f"SentenceModel={_global_settings.sentence_model}",
            f"Platform={os.name}",
            "Framework=pytest + selenium",
        ]
    )
    env_file.write_text(env_content)

    # Allure categories (for triage)
    categories = [
        {
            "name": "AI Validation Failures",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*similarity.*|.*hallucination.*|.*semantic.*",
        },
        {
            "name": "Security Violations",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*forbidden.*|.*injection.*|.*XSS.*",
        },
        {
            "name": "UI / Layout Failures",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*direction.*|.*RTL.*|.*LTR.*|.*widget.*",
        },
        {
            "name": "Timeout Failures",
            "matchedStatuses": ["failed", "broken"],
            "messageRegex": ".*TimeoutException.*|.*timed out.*",
        },
    ]
    categories_file = results_dir / "categories.json"
    categories_file.write_text(json.dumps(categories, indent=2))


# ── per-phase report hook ─────────────────────────────────────────────────────


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call):
    """Stash the result of each test phase so teardown fixtures can read it."""
    outcome = yield
    report = outcome.get_result()
    # Store on the item node so fixtures can read it via request.node
    setattr(item, f"_report_{report.when}", report)


# ── Session-scoped fixtures ───────────────────────────────────────────────────


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Provide the global Settings singleton to all tests."""
    return _global_settings


@pytest.fixture(scope="session")
def test_data(settings: Settings) -> dict:
    """
    Load and return the parsed test-data.json corpus.
    Validates the schema version on load.
    """
    data_path = Path(__file__).parent.parent / "data" / "test-data.json"
    log.info("Loading test data from: %s", data_path)
    with open(data_path, encoding="utf-8") as fh:
        data = json.load(fh)

    version = data.get("version", "unknown")
    log.info("Test data version: %s  (%d cases)", version, len(data.get("test_cases", [])))
    return data


@pytest.fixture(scope="session")
def ai_validator(settings: Settings) -> AIValidator:
    """
    Session-scoped AI validator.
    The sentence-transformer model is loaded ONCE per test session (~2–5 s).
    """
    log.info("Initialising AIValidator (model=%s)", settings.sentence_model)
    validator = AIValidator(
        model_name=settings.sentence_model,
        threshold=settings.similarity_threshold,
    )
    return validator


# ── Function-scoped fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="function")
def driver(request: pytest.FixtureRequest, settings: Settings) -> Generator[WebDriver, None, None]:
    """
    Create a fresh WebDriver for each test.

    When CHROME_DEBUG_PORT is set the driver attaches to an existing Chrome
    session instead of launching a new one. In that mode the browser is NOT
    quit at teardown so the user's session stays alive.

    Teardown:
      1. Capture screenshot if the test FAILED (call phase)
      2. Attach screenshot to Allure
      3. quit() the driver (skipped when using remote debugging)
    """
    using_existing = bool(settings.chrome_debug_port)
    log.info(
        "%s driver for test: %s",
        "Attaching to existing Chrome" if using_existing else f"Creating {settings.browser}",
        request.node.nodeid,
    )
    web_driver = DriverFactory.create(settings)

    yield web_driver

    # ── Teardown ─────────────────────────────────────────────────────────────
    call_report = getattr(request.node, "_report_call", None)
    if call_report and call_report.failed and settings.screenshot_on_failure:
        test_name = request.node.name
        helper = ScreenshotHelper(web_driver, settings)
        log.warning("Test FAILED – capturing screenshot: %s", test_name)
        helper.capture_on_failure(test_name)

    if using_existing:
        log.info("Leaving existing Chrome session open after test: %s", request.node.nodeid)
    else:
        log.info("Quitting driver for test: %s", request.node.nodeid)
        try:
            web_driver.quit()
        except Exception as exc:
            log.warning("Error quitting driver: %s", exc)


@pytest.fixture(scope="function")
def chatbot_page(driver: WebDriver, settings: Settings) -> ChatbotPage:
    """
    Provide an open, ready-to-use ChatbotPage for each test.
    The page is navigated to the chatbot URL and the widget is activated.
    """
    page = ChatbotPage(driver, settings)
    page.open_and_activate()
    return page


# ── Parametrised helper fixtures ──────────────────────────────────────────────
# These are used in individual test files with pytest.mark.parametrize.
# Kept here as convenience factories.


def get_cases_by_suite(test_data: dict, suite: str, language: str = "all") -> list:
    """Filter test_cases by suite and optional language."""
    cases = [
        tc for tc in test_data.get("test_cases", [])
        if tc.get("suite") == suite
        and (language == "all" or tc.get("language") == language)
    ]
    return cases


def get_case_ids(cases: list) -> list:
    """Return IDs for pytest.mark.parametrize."""
    return [tc["id"] for tc in cases]
