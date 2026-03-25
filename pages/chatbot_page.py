"""
pages/chatbot_page.py
─────────────────────
Page object for the U-Ask chatbot widget.
Live URL: https://beta-ask.u.ae/en/uask

ARCHITECTURE NOTE:
  U-Ask is an Angular Single-Page Application (confirmed via static analysis).
  The entire UI is rendered by Angular inside <app-root class="vh-100">.
  None of the chat widget elements appear in the static HTML source — they are
  injected into the DOM at runtime by JavaScript.

  This means:
    · Selectors CANNOT be discovered by viewing page source (Ctrl+U)
    · Selectors MUST be found using Chrome DevTools on the live rendered page
    · The framework waits for Angular to finish rendering before interacting

HOW TO FIND THE REAL SELECTORS (one-time setup):
  1. Open https://beta-ask.u.ae/en/uask in Chrome
  2. Wait for the page to fully load (Angular bootstrap takes ~1-2 s)
  3. Press F12 to open DevTools → Elements tab
  4. For each element below, right-click it in the browser → Inspect
  5. Look for stable attributes in this priority order:
       a. data-testid="..."     ← most stable, won't change with styling
       b. id="..."              ← stable if not auto-generated
       c. aria-label="..."      ← accessible and stable
       d. a unique class name   ← use only if specific (not generic like "btn")
  6. Paste the selector into the corresponding constant below
  7. Run: make test-smoke  to verify all selectors work

ELEMENTS TO INSPECT:
  · The chat input box      → INPUT_FIELD
  · The send / submit btn   → SEND_BUTTON
  · Bot response bubbles    → RESPONSE_BUBBLE
  · Typing / loading dots   → TYPING_INDICATOR
  · Language toggle EN/AR   → LANG_TOGGLE_EN / LANG_TOGGLE_AR
  · Outer chat container    → CHAT_CONTAINER
  · User message bubbles    → USER_MESSAGE
  · Clear / new chat button → CLEAR_BUTTON

ANGULAR-SPECIFIC TIPS:
  · Angular adds _ngcontent-xxx-c### attributes to elements — avoid these,
    they change with every build. Use data-testid or aria-label instead.
  · If you see mat-input-element or MatFormField classes, this app uses
    Angular Material — selectors like 'mat-form-field textarea' are stable.
  · Check for [formControl] or [formControlName] attributes on input fields.
"""
from __future__ import annotations

import time
from typing import List, Optional

import allure
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from pages.base_page import BasePage, Locator


class ChatbotPage(BasePage):
    """Encapsulates all interactions with the U-Ask chatbot widget."""

    # ── Locators ──────────────────────────────────────────────────────────────
    # STATUS: Placeholder selectors — must be updated after browser inspection.
    #
    # The site is Angular-rendered. Open https://beta-ask.u.ae/en/uask in Chrome,
    # press F12, and replace each selector below with the real one you find.
    # See the module docstring above for step-by-step instructions.
    #
    # Format: (By.CSS_SELECTOR, "your-selector-here")
    # Selector priority: data-testid > id > aria-label > unique class name
    # ──────────────────────────────────────────────────────────────────────────

    # Angular app root — always present, used to confirm Angular has bootstrapped
    APP_ROOT = (By.TAG_NAME, "app-root")

    # Chat widget trigger button (floating bubble or "Ask" button)
    # TODO: Inspect and replace — look for button near bottom-right of screen
    CHATBOT_TRIGGER = (
        By.CSS_SELECTOR,
        "[data-testid='chat-trigger'], "
        "button[aria-label*='ask' i], "
        "button[aria-label*='chat' i], "
        ".chat-bubble, "
        ".uask-trigger",
    )

    # Outer chat container (the panel/card that wraps the whole widget)
    # TODO: Inspect and replace — likely a mat-card, div[role='dialog'], or similar
    CHAT_CONTAINER = (
        By.CSS_SELECTOR,
        "[data-testid='chat-container'], "
        "app-chat, "
        "app-chatbot, "
        ".chat-container, "
        "mat-card.chat",
    )

    # Text input field where the user types their message
    # TODO: Inspect and replace — Angular Material textarea is common:
    #       mat-form-field textarea   or   textarea[formcontrolname]
    INPUT_FIELD = (
        By.CSS_SELECTOR,
        "textarea[data-testid='chat-input'], "
        "textarea[formcontrolname='message'], "
        "textarea[placeholder*='message' i], "
        "textarea[placeholder*='اكتب' i], "
        "textarea[placeholder*='type' i], "
        "mat-form-field textarea, "
        "input[type='text'][placeholder*='message' i]",
    )

    # Send / submit button
    # TODO: Inspect and replace — look for button next to the input field
    SEND_BUTTON = (
        By.CSS_SELECTOR,
        "button[data-testid='send-button'], "
        "button[aria-label*='send' i], "
        "button[type='submit'], "
        ".send-button, "
        "mat-icon-button[aria-label*='send' i]",
    )

    # Bot (AI) response message bubbles
    # TODO: Inspect and replace — look for elements containing AI-generated text
    RESPONSE_BUBBLE = (
        By.CSS_SELECTOR,
        "[data-testid='bot-message'], "
        "app-bot-message, "
        ".bot-message, "
        ".ai-message, "
        ".assistant-message, "
        ".message-bubble.bot",
    )

    # Typing / loading indicator (the "..." dots while AI is thinking)
    # TODO: Inspect and replace — may be an Angular animation component
    TYPING_INDICATOR = (
        By.CSS_SELECTOR,
        "[data-testid='typing-indicator'], "
        "app-typing-indicator, "
        ".typing-indicator, "
        ".loading-dots, "
        ".is-typing",
    )

    # Language toggle buttons (EN / AR)
    # TODO: Inspect and replace — may be a dropdown, tabs, or top-nav buttons
    LANG_TOGGLE_EN = (
        By.CSS_SELECTOR,
        "[data-lang='en'], "
        "button[aria-label='English'], "
        "a[href*='/en/'], "
        ".lang-en",
    )
    LANG_TOGGLE_AR = (
        By.CSS_SELECTOR,
        "[data-lang='ar'], "
        "button[aria-label='العربية'], "
        "a[href*='/ar/'], "
        ".lang-ar",
    )

    # Fallback / error message displayed when the AI cannot respond
    # TODO: Inspect and replace — may not exist if the app uses inline error text
    FALLBACK_MESSAGE = (
        By.CSS_SELECTOR,
        "[data-testid='error-message'], "
        "app-error-message, "
        ".error-message, "
        ".fallback-message",
    )

    # "New chat" / "Clear conversation" button
    # TODO: Inspect and replace
    CLEAR_BUTTON = (
        By.CSS_SELECTOR,
        "button[data-testid='new-chat'], "
        "button[aria-label*='new chat' i], "
        "button[aria-label*='clear' i], "
        ".new-chat",
    )

    # User's own message bubble
    # TODO: Inspect and replace
    USER_MESSAGE = (
        By.CSS_SELECTOR,
        "[data-testid='user-message'], "
        "app-user-message, "
        ".user-message, "
        ".human-message",
    )

    # All messages in the conversation (both user + bot)
    ALL_MESSAGES = (
        By.CSS_SELECTOR,
        "[data-testid='message'], "
        "app-message, "
        ".chat-message, "
        ".message-bubble",
    )

    # ── Initialisation ────────────────────────────────────────────────────────

    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        super().__init__(driver, settings)
        self._in_iframe: bool = False

    # ── High-level workflow ───────────────────────────────────────────────────

    @allure.step("Open chatbot page")
    def open(self) -> "ChatbotPage":
        """Navigate to the chatbot URL and wait for the Angular app to boot."""
        self.log.info("Opening chatbot at: %s", self.settings.chatbot_url)
        self.driver.get(self.settings.chatbot_url)
        self.wait_for_page_ready()
        self._wait_for_angular_bootstrap()
        return self

    @allure.step("Open and activate chatbot widget")
    def open_and_activate(self) -> "ChatbotPage":
        """Open the page, wait for Angular to render, then activate the widget."""
        self.open()
        self._activate_widget_if_needed()
        return self

    def wait_for_page_ready(self) -> None:
        """Wait until document.readyState is complete."""
        try:
            self._wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            self.log.warning("Page readyState did not reach 'complete' in time")

    def _wait_for_angular_bootstrap(self) -> None:
        """
        Wait for Angular to finish its initial rendering cycle.

        U-Ask is an Angular SPA. After the page loads, Angular bootstraps
        inside <app-root> and renders the entire UI dynamically.
        We wait for app-root to have child elements before attempting
        to interact with anything.
        """
        self.log.info("Waiting for Angular to bootstrap inside <app-root>...")
        try:
            self._wait.until(
                lambda d: d.execute_script(
                    "var root = document.querySelector('app-root');"
                    "return root && root.children.length > 0;"
                )
            )
            self.log.info("Angular bootstrap complete.")
        except TimeoutException:
            self.log.warning(
                "app-root did not receive child elements in time. "
                "Angular may still be loading — proceeding anyway."
            )
        # Additional buffer for Angular's async change detection
        self.pause(1.5)

    # ── Widget activation ──────────────────────────────────────────────────────

    def _activate_widget_if_needed(self) -> None:
        """Click the floating chat trigger if the input is not already visible."""
        if not self.is_element_visible(self.INPUT_FIELD, timeout=3):
            if self.is_element_visible(self.CHATBOT_TRIGGER, timeout=5):
                self.log.info("Clicking chatbot trigger button")
                self.safe_click(self.CHATBOT_TRIGGER)
                # Give the widget animation time to finish
                self.pause(1.0)
            else:
                self.log.warning(
                    "Neither chat trigger nor input field found – widget may be "
                    "embedded directly or in an iframe"
                )
            self._switch_to_chat_iframe_if_present()

    def _switch_to_chat_iframe_if_present(self) -> None:
        """If the chat widget is inside an iframe, switch to it."""
        try:
            iframe = self.driver.find_element(
                By.CSS_SELECTOR, "iframe[title*='chat' i], iframe[src*='chat']"
            )
            self.driver.switch_to.frame(iframe)
            self._in_iframe = True
            self.log.info("Switched into chat iframe")
        except Exception:
            pass  # No iframe – widget is embedded directly in the page

    def switch_to_main_content(self) -> None:
        """Switch back to the main frame (call after finishing iframe interactions)."""
        if self._in_iframe:
            self.driver.switch_to.default_content()
            self._in_iframe = False

    # ── Messaging ─────────────────────────────────────────────────────────────

    @allure.step("Type message: {text}")
    def type_message(self, text: str) -> "ChatbotPage":
        self.log.info("Typing message: %.60s…", text)
        input_el = self.wait_for_visible(self.INPUT_FIELD)
        input_el.clear()
        input_el.send_keys(text)
        return self

    @allure.step("Submit message")
    def submit_message(self) -> "ChatbotPage":
        """Click Send button (or press Enter if button not found)."""
        if self.is_element_visible(self.SEND_BUTTON, timeout=2):
            self.safe_click(self.SEND_BUTTON)
        else:
            input_el = self.wait_for_visible(self.INPUT_FIELD)
            input_el.send_keys(Keys.RETURN)
        return self

    @allure.step("Send message and wait for response: {text}")
    def send_message(self, text: str, wait_for_response: bool = True) -> "ChatbotPage":
        """Type and send a message, then optionally wait for the AI response."""
        self.type_message(text)
        # Respect inter-message delay to avoid rate-limiting
        self.pause(self.settings.inter_message_delay)
        self.submit_message()
        if wait_for_response:
            self.wait_for_response_complete()
        return self

    # ── Response utilities ────────────────────────────────────────────────────

    @allure.step("Wait for AI response to complete")
    def wait_for_response_complete(
        self, timeout: Optional[int] = None
    ) -> "ChatbotPage":
        """
        Wait until:
        1. The typing indicator disappears, AND
        2. At least one bot response bubble is visible.
        """
        t = timeout or self.settings.explicit_wait
        # Wait for typing indicator to appear first (up to 5 s)
        try:
            WebDriverWait(self.driver, 5).until(
                lambda d: d.find_elements(*self.TYPING_INDICATOR)
            )
        except Exception:
            pass  # Typing indicator may not exist in all implementations

        # Wait for typing indicator to disappear
        self.wait_for_element_to_disappear(self.TYPING_INDICATOR, timeout=t)

        # Wait for a bot response to be present
        try:
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            WebDriverWait(self.driver, t).until(
                EC.presence_of_element_located(self.RESPONSE_BUBBLE)
            )
        except TimeoutException:
            self.log.warning("No bot response bubble found within %s seconds", t)
        return self

    def get_all_responses(self) -> List[str]:
        """Return normalised text of ALL bot response bubbles."""
        elements = self.driver.find_elements(*self.RESPONSE_BUBBLE)
        return [self._normalise_text(el.text) for el in elements]

    def get_last_response(self) -> str:
        """Return normalised text of the most recent bot response."""
        responses = self.get_all_responses()
        return responses[-1] if responses else ""

    def get_response_count(self) -> int:
        return len(self.driver.find_elements(*self.RESPONSE_BUBBLE))

    def get_response_text_direction(self) -> str:
        """Return the text direction ('ltr' or 'rtl') of the last response bubble."""
        elements = self.driver.find_elements(*self.RESPONSE_BUBBLE)
        if not elements:
            return "ltr"
        last = elements[-1]
        attr = last.get_attribute("dir") or ""
        if attr.lower() in ("rtl", "ltr"):
            return attr.lower()
        return self.driver.execute_script(
            "return window.getComputedStyle(arguments[0]).direction;", last
        ) or "ltr"

    # ── Input state queries ────────────────────────────────────────────────────

    def get_input_value(self) -> str:
        """Return current text in the input field."""
        try:
            el = self.wait_for_element(self.INPUT_FIELD, timeout=5)
            return el.get_attribute("value") or el.text or ""
        except TimeoutException:
            return ""

    def is_input_empty(self) -> bool:
        return self.get_input_value().strip() == ""

    def is_input_disabled(self) -> bool:
        try:
            el = self.wait_for_element(self.INPUT_FIELD, timeout=3)
            return el.get_attribute("disabled") is not None
        except TimeoutException:
            return True  # Can't find it – treat as unavailable

    def is_send_button_visible(self) -> bool:
        return self.is_element_visible(self.SEND_BUTTON, timeout=3)

    # ── Fallback / Error states ───────────────────────────────────────────────

    def is_fallback_message_visible(self) -> bool:
        return self.is_element_visible(self.FALLBACK_MESSAGE, timeout=5)

    def get_fallback_text(self) -> str:
        if self.is_fallback_message_visible():
            return self.get_element_text(self.FALLBACK_MESSAGE)
        return ""

    # ── Widget visibility ─────────────────────────────────────────────────────

    def is_chat_widget_visible(self) -> bool:
        """True if either the trigger or the open widget is on screen."""
        return self.is_element_visible(
            self.CHATBOT_TRIGGER, timeout=5
        ) or self.is_element_visible(self.INPUT_FIELD, timeout=5)

    def is_chat_input_visible(self) -> bool:
        return self.is_element_visible(self.INPUT_FIELD, timeout=5)

    # ── Language switching ────────────────────────────────────────────────────

    @allure.step("Switch chatbot language to: {language}")
    def switch_language(self, language: str) -> "ChatbotPage":
        """
        Switch the chatbot (and/or the site) to the given language ('en' or 'ar').
        """
        locator = self.LANG_TOGGLE_AR if language.lower() == "ar" else self.LANG_TOGGLE_EN
        if self.is_element_visible(locator, timeout=3):
            self.safe_click(locator)
            self.pause(1.0)
        else:
            self.log.warning(
                "Language toggle for '%s' not found – site may default to this language",
                language,
            )
        return self

    # ── Conversation management ───────────────────────────────────────────────

    @allure.step("Clear conversation history")
    def clear_conversation(self) -> "ChatbotPage":
        if self.is_element_visible(self.CLEAR_BUTTON, timeout=3):
            self.safe_click(self.CLEAR_BUTTON)
            self.pause(0.5)
        return self

    # ── Scrolling within the chat ──────────────────────────────────────────────

    def scroll_chat_to_bottom(self) -> "ChatbotPage":
        if self.is_element_present(self.CHAT_CONTAINER):
            self.scroll_element_to_bottom(self.CHAT_CONTAINER)
        return self

    # ── Accessibility helpers ─────────────────────────────────────────────────

    def get_input_aria_label(self) -> str:
        return self.get_element_attribute(self.INPUT_FIELD, "aria-label")

    def get_send_button_aria_label(self) -> str:
        return self.get_element_attribute(self.SEND_BUTTON, "aria-label")

    # ── Convenience: full send-and-read cycle ─────────────────────────────────

    @allure.step("Send prompt and capture response")
    def send_and_get_response(self, prompt: str) -> str:
        """
        High-level helper used by tests:
          1. Send the prompt
          2. Wait for the response
          3. Return the normalised response text
        """
        response_count_before = self.get_response_count()
        self.send_message(prompt)

        # Wait until at least one NEW response bubble appears
        deadline = time.time() + self.settings.explicit_wait
        while time.time() < deadline:
            if self.get_response_count() > response_count_before:
                break
            time.sleep(0.5)

        return self.get_last_response()
