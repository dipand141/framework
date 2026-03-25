"""
tests/base_test.py
──────────────────
Base test class that all test classes inherit from.

Responsibilities:
  - Assertion helpers (with Allure steps and rich failure messages)
  - Convenience wrappers for common chatbot interactions
  - Allure attachment helpers

Note on pytest fixture injection:
  Fixtures declared in conftest.py are injected into test METHOD parameters,
  not into __init__.  Base class methods that need fixtures (e.g. ai_validator)
  receive them as parameters – there is no __init__ here.
"""
from __future__ import annotations

from typing import List, Optional

import allure

from utils.ai_validator import AIValidator, ValidationResult
from utils.logger import get_logger

log = get_logger("base_test")


class BaseTest:
    """
    Shared assertion helpers and Allure wrappers.
    Inherit from this in every test class.
    """

    # ── Response / text assertions ────────────────────────────────────────────

    @staticmethod
    @allure.step("Assert response contains keyword(s): {keywords}")
    def assert_response_contains_keyword(response: str, keywords: List[str]) -> None:
        """
        Assert that at least ONE of the given keywords appears in the response
        (case-insensitive).
        """
        response_lower = response.lower()
        found = [kw for kw in keywords if kw.lower() in response_lower]
        assert found, (
            f"Expected at least one keyword from {keywords!r} in response, but none found.\n"
            f"Response: {response[:500]!r}"
        )
        log.info("Keyword check passed – found: %s", found)

    @staticmethod
    @allure.step("Assert response does NOT contain forbidden content")
    def assert_no_forbidden_content(response: str, forbidden: List[str]) -> None:
        """Assert that NONE of the forbidden strings appear in the response."""
        import re

        violations = []
        for pattern in forbidden:
            if re.search(pattern, response, re.IGNORECASE | re.DOTALL):
                violations.append(pattern)

        assert not violations, (
            f"Forbidden content found in response!\n"
            f"Violations: {violations!r}\n"
            f"Response: {response[:500]!r}"
        )

    @staticmethod
    @allure.step("Assert response is not empty")
    def assert_response_not_empty(response: str) -> None:
        assert response and response.strip(), (
            "Expected a non-empty chatbot response, but got an empty string."
        )

    @staticmethod
    @allure.step("Assert response length is reasonable")
    def assert_response_length(
        response: str, min_chars: int = 20, max_chars: int = 5000
    ) -> None:
        length = len(response.strip())
        assert min_chars <= length <= max_chars, (
            f"Response length {length} outside expected range "
            f"[{min_chars}, {max_chars}].\nResponse: {response[:200]!r}"
        )

    # ── AI / Semantic assertions ──────────────────────────────────────────────

    @allure.step("Assert semantic relevance above threshold")
    def assert_semantic_relevance(
        self,
        response: str,
        concepts: List[str],
        ai_validator: AIValidator,
        threshold: Optional[float] = None,
    ) -> ValidationResult:
        """
        Run full AI validation and assert it passes.
        Returns the ValidationResult for further inspection.
        """
        result = ai_validator.validate_response(
            response=response,
            expected_concepts=concepts,
            attach_to_allure=True,
        )
        t = threshold or ai_validator.threshold
        assert result.max_similarity_score >= t, (
            f"Semantic similarity {result.max_similarity_score:.4f} is below "
            f"threshold {t:.4f}.\n"
            f"Concepts: {concepts!r}\n"
            f"Response: {response[:400]!r}"
        )
        return result

    @allure.step("Assert response language matches: {expected_language}")
    def assert_response_language(
        self,
        response: str,
        expected_language: str,
        ai_validator: AIValidator,
    ) -> None:
        """Assert the response text is in the expected language."""
        lang_match = ai_validator._check_language_consistency(response, expected_language)
        if lang_match is None:
            log.warning(
                "Language detection unavailable – skipping language assertion for '%s'",
                expected_language,
            )
            return
        assert lang_match, (
            f"Response language does not match expected '{expected_language}'.\n"
            f"Response (first 200 chars): {response[:200]!r}"
        )

    # ── Layout / Direction assertions ─────────────────────────────────────────

    @staticmethod
    @allure.step("Assert page layout is LTR (left-to-right)")
    def assert_ltr_layout(chatbot_page) -> None:
        direction = chatbot_page.get_page_text_direction()
        assert direction == "ltr", (
            f"Expected LTR page layout, but found: '{direction}'"
        )

    @staticmethod
    @allure.step("Assert page layout is RTL (right-to-left)")
    def assert_rtl_layout(chatbot_page) -> None:
        direction = chatbot_page.get_page_text_direction()
        assert direction == "rtl", (
            f"Expected RTL page layout, but found: '{direction}'"
        )

    @staticmethod
    @allure.step("Assert response bubble text direction is: {expected_direction}")
    def assert_response_direction(chatbot_page, expected_direction: str) -> None:
        direction = chatbot_page.get_response_text_direction()
        assert direction == expected_direction.lower(), (
            f"Expected response text direction '{expected_direction}', "
            f"but found '{direction}'"
        )

    # ── Widget / UI assertions ────────────────────────────────────────────────

    @staticmethod
    @allure.step("Assert chat widget is visible")
    def assert_widget_visible(chatbot_page) -> None:
        assert chatbot_page.is_chat_widget_visible(), (
            "Chat widget (trigger button or input field) is not visible on the page."
        )

    @staticmethod
    @allure.step("Assert chat input field is visible")
    def assert_input_visible(chatbot_page) -> None:
        assert chatbot_page.is_chat_input_visible(), (
            "Chat input field is not visible."
        )

    @staticmethod
    @allure.step("Assert input field is empty after message was sent")
    def assert_input_cleared(chatbot_page) -> None:
        assert chatbot_page.is_input_empty(), (
            f"Input field should be empty after sending, "
            f"but contains: {chatbot_page.get_input_value()!r}"
        )

    @staticmethod
    @allure.step("Assert at least one AI response is visible")
    def assert_response_visible(chatbot_page) -> None:
        response = chatbot_page.get_last_response()
        assert response and response.strip(), (
            "Expected at least one AI response bubble, but none found."
        )

    # ── Allure utilities ──────────────────────────────────────────────────────

    @staticmethod
    def attach_prompt_response(
        prompt: str,
        response: str,
        language: str = "",
        score: Optional[float] = None,
    ) -> None:
        """Attach a formatted prompt/response pair to the Allure report."""
        lines = [
            f"Language : {language or 'N/A'}",
            f"Prompt   : {prompt}",
            "─" * 50,
            f"Response : {response}",
        ]
        if score is not None:
            lines.append(f"Sim Score: {score:.4f}")
        allure.attach(
            "\n".join(lines),
            name="Prompt & Response",
            attachment_type=allure.attachment_type.TEXT,
        )

    @staticmethod
    def attach_text(content: str, name: str = "Details") -> None:
        allure.attach(
            content,
            name=name,
            attachment_type=allure.attachment_type.TEXT,
        )

    # ── Convenience: full interaction cycle ───────────────────────────────────

    @staticmethod
    @allure.step("Send prompt and capture chatbot response")
    def send_and_capture(chatbot_page, prompt: str) -> str:
        """Send a prompt and return the normalised response text."""
        return chatbot_page.send_and_get_response(prompt)
