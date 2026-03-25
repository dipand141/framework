"""
utils/driver_factory.py
───────────────────────
Factory that creates a configured Selenium WebDriver instance.
Supports Chrome, Firefox, Edge (local) and Selenium Grid (remote).
Handles mobile emulation and headless mode.
"""
from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from config.settings import Settings
from utils.logger import get_logger

log = get_logger(__name__)


class DriverFactory:
    """Creates and configures WebDriver instances."""

    @staticmethod
    def create(settings: Settings) -> WebDriver:
        """
        Instantiate the correct WebDriver based on settings.
        Returns a fully configured driver ready for use.
        """
        if settings.selenium_grid_url:
            return DriverFactory._create_remote(settings)

        browser = settings.browser.lower()
        if browser == "chrome":
            return DriverFactory._create_chrome(settings)
        if browser == "firefox":
            return DriverFactory._create_firefox(settings)
        if browser == "edge":
            return DriverFactory._create_edge(settings)

        raise ValueError(
            f"Unsupported browser: '{browser}'. Choose chrome, firefox, or edge."
        )

    # ── Chrome ────────────────────────────────────────────────────────────────

    @staticmethod
    def _create_chrome(settings: Settings) -> WebDriver:
        options = ChromeOptions()

        if settings.headless:
            options.add_argument("--headless=new")

        # Stability / automation flags
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-infobars")

        # Window size
        options.add_argument("--window-size=1920,1080")

        if settings.mobile_emulation:
            mobile_emulation = {"deviceName": settings.mobile_device}
            options.add_experimental_option("mobileEmulation", mobile_emulation)
            log.info("Mobile emulation enabled: %s", settings.mobile_device)

        # Language – set Accept-Language to match test language
        # This prevents locale-based UI divergence between runs
        prefs: dict = {
            "intl.accept_languages": "en-US,en",
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
        options.add_experimental_option("prefs", prefs)

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(settings.implicit_wait)
        driver.maximize_window()

        log.info(
            "Chrome driver created (headless=%s, mobile=%s)",
            settings.headless,
            settings.mobile_emulation,
        )
        return driver

    # ── Firefox ───────────────────────────────────────────────────────────────

    @staticmethod
    def _create_firefox(settings: Settings) -> WebDriver:
        options = FirefoxOptions()

        if settings.headless:
            options.add_argument("--headless")

        options.set_preference("intl.accept_languages", "en-US, en")
        options.set_preference("general.useragent.override", "")

        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        driver.implicitly_wait(settings.implicit_wait)
        driver.maximize_window()

        log.info("Firefox driver created (headless=%s)", settings.headless)
        return driver

    # ── Edge ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _create_edge(settings: Settings) -> WebDriver:
        options = EdgeOptions()

        if settings.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
        driver.implicitly_wait(settings.implicit_wait)
        driver.maximize_window()

        log.info("Edge driver created (headless=%s)", settings.headless)
        return driver

    # ── Remote / Selenium Grid ────────────────────────────────────────────────

    @staticmethod
    def _create_remote(settings: Settings) -> WebDriver:
        browser = settings.browser.lower()

        if browser == "chrome":
            options = ChromeOptions()
            if settings.headless:
                options.add_argument("--headless=new")
        elif browser == "firefox":
            options = FirefoxOptions()
            if settings.headless:
                options.add_argument("--headless")
        else:
            options = EdgeOptions()

        driver = webdriver.Remote(
            command_executor=settings.selenium_grid_url,
            options=options,
        )
        driver.implicitly_wait(settings.implicit_wait)

        log.info(
            "Remote driver created: grid=%s browser=%s",
            settings.selenium_grid_url,
            browser,
        )
        return driver
