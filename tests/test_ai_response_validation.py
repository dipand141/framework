"""
tests/test_ai_response_validation.py
─────────────────────────────────────
Suite B — Data / AI Response Quality Tests  (11 test cases)
Target: https://beta-ask.u.ae/en/uask  (Angular SPA)

Test cases (approved):
  TC_DATA_EN_001  Emirates ID renewal — English
  TC_DATA_EN_002  Nol card registration — English
  TC_DATA_EN_003  UAE residence visa documents — English
  TC_DATA_EN_004  DEWA electricity connection — English
  TC_DATA_EN_005  Traffic fine payment Dubai — English
  TC_DATA_AR_001  Emirates ID renewal — Arabic
  TC_DATA_AR_002  Nol card registration — Arabic
  TC_DATA_AR_003  DEWA electricity connection — Arabic
  TC_DATA_CONS_001  Cross-language consistency EN vs AR (Emirates ID)
  TC_DATA_EDGE_001  Gibberish input — graceful fallback
  TC_DATA_EDGE_002  Repeated question consistency

All prompts and expected values are loaded from data/test-data.json.
"""
from __future__ import annotations

import json
from pathlib import Path

import allure
import pytest

from config.settings import Settings
from pages.chatbot_page import ChatbotPage
from tests.base_test import BaseTest
from utils.ai_validator import AIValidator

# ── Load test data ────────────────────────────────────────────────────────────
_DATA = json.loads(
    (Path(__file__).parent.parent / "data" / "test-data.json").read_text(encoding="utf-8")
)
_DATA_TESTS = {tc["id"]: tc for tc in _DATA["data_tests"]}

# Parametrize helpers
_EN_CASES = [tc for tc in _DATA["data_tests"] if tc["language"] == "en" and tc["id"].startswith("TC_DATA_EN")]
_AR_CASES = [tc for tc in _DATA["data_tests"] if tc["language"] == "ar" and tc["id"].startswith("TC_DATA_AR")]


# ─────────────────────────────────────────────────────────────────────────────
# TC_DATA_EN_001 – TC_DATA_EN_005   English Public Service Queries
# ─────────────────────────────────────────────────────────────────────────────

@allure.feature("Data / AI Response Quality")
@allure.story("English Public Service Queries")
@pytest.mark.ai_validation
@pytest.mark.english
class TestEnglishDataQueries(BaseTest):

    @allure.title("{tc[id]} — {tc[title]}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("tc", _EN_CASES, ids=[t["id"] for t in _EN_CASES])
    def test_english_query(
        self,
        tc: dict,
        chatbot_page: ChatbotPage,
        ai_validator: AIValidator,
        settings: Settings,
    ) -> None:
        """
        Data-driven test for each English public service query.

        Validation pipeline per response:
          1. Response is not empty
          2. At least one expected keyword is present (case-insensitive)
          3. Semantic similarity to expected concepts >= min_similarity
          4. No forbidden patterns (raw HTML, error codes, undefined)
        """
        if not settings.should_run_english():
            pytest.skip("English tests disabled via TEST_LANGUAGE setting")

        allure.dynamic.description(tc["description"])

        with allure.step(f"Send prompt: {tc['prompt']}"):
            response = self.send_and_capture(chatbot_page, tc["prompt"])

        with allure.step("Assert response is not empty"):
            self.assert_response_not_empty(response)

        with allure.step(f"Assert keyword presence — looking for any of: {tc['expected_keywords']}"):
            if tc["expected_keywords"]:
                self.assert_response_contains_keyword(response, tc["expected_keywords"])

        with allure.step(f"Assert semantic relevance (threshold: {tc['min_similarity']})"):
            result = ai_validator.validate_response(
                response=response,
                expected_concepts=tc["expected_semantic_concepts"],
                forbidden_patterns=tc["forbidden_patterns"],
                prompt=tc["prompt"],
                language="en",
                attach_to_allure=True,
            )
            self.attach_prompt_response(
                prompt=tc["prompt"],
                response=response,
                language="en",
                score=result.max_similarity_score,
            )
            assert result.max_similarity_score >= tc["min_similarity"], (
                f"[{tc['id']}] Semantic similarity {result.max_similarity_score:.4f} "
                f"is below threshold {tc['min_similarity']}.\n"
                f"Response: {response[:400]!r}"
            )

        with allure.step("Assert no forbidden content in response"):
            assert not result.forbidden_violations, (
                f"[{tc['id']}] Forbidden patterns found: {result.forbidden_violations}\n"
                f"Response: {response[:400]!r}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# TC_DATA_AR_001 – TC_DATA_AR_003   Arabic Public Service Queries
# ─────────────────────────────────────────────────────────────────────────────

@allure.feature("Data / AI Response Quality")
@allure.story("Arabic Public Service Queries")
@pytest.mark.ai_validation
@pytest.mark.arabic
class TestArabicDataQueries(BaseTest):

    @allure.title("{tc[id]} — {tc[title]}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("tc", _AR_CASES, ids=[t["id"] for t in _AR_CASES])
    def test_arabic_query(
        self,
        tc: dict,
        chatbot_page: ChatbotPage,
        ai_validator: AIValidator,
        settings: Settings,
    ) -> None:
        """
        Data-driven test for each Arabic public service query.

        The multilingual sentence-transformer model shares an embedding space
        for Arabic and English, so Arabic responses are compared directly to
        English-language expected semantic concepts — no translation needed.

        Validation pipeline:
          1. Switch to Arabic URL / language
          2. Response is not empty
          3. At least one Arabic keyword is present
          4. Semantic similarity (EN concepts vs AR response) >= min_similarity
          5. No forbidden patterns
          6. Language detection confirms response is in Arabic
        """
        if not settings.should_run_arabic():
            pytest.skip("Arabic tests disabled via TEST_LANGUAGE setting")

        allure.dynamic.description(tc["description"])

        with allure.step("Navigate to Arabic chatbot URL"):
            chatbot_page.driver.get("https://beta-ask.u.ae/ar/uask")
            chatbot_page.wait_for_page_ready()
            chatbot_page._wait_for_angular_bootstrap()
            chatbot_page._activate_widget_if_needed()

        with allure.step(f"Send Arabic prompt: {tc['prompt']}"):
            response = self.send_and_capture(chatbot_page, tc["prompt"])

        with allure.step("Assert response is not empty"):
            self.assert_response_not_empty(response)

        with allure.step(f"Assert Arabic keyword presence — looking for any of: {tc['expected_keywords']}"):
            if tc["expected_keywords"]:
                self.assert_response_contains_keyword(response, tc["expected_keywords"])

        with allure.step(f"Assert semantic relevance via multilingual model (threshold: {tc['min_similarity']})"):
            result = ai_validator.validate_response(
                response=response,
                expected_concepts=tc["expected_semantic_concepts"],
                forbidden_patterns=tc["forbidden_patterns"],
                prompt=tc["prompt"],
                language="ar",
                attach_to_allure=True,
            )
            self.attach_prompt_response(
                prompt=tc["prompt"],
                response=response,
                language="ar",
                score=result.max_similarity_score,
            )
            assert result.max_similarity_score >= tc["min_similarity"], (
                f"[{tc['id']}] Semantic similarity {result.max_similarity_score:.4f} "
                f"is below threshold {tc['min_similarity']}.\n"
                f"Response: {response[:400]!r}"
            )

        with allure.step("Assert no forbidden content in response"):
            assert not result.forbidden_violations, (
                f"[{tc['id']}] Forbidden patterns found: {result.forbidden_violations}"
            )

        with allure.step("Assert response language is Arabic"):
            self.assert_response_language(response, "ar", ai_validator)


# ─────────────────────────────────────────────────────────────────────────────
# TC_DATA_CONS_001   Cross-language Consistency
# ─────────────────────────────────────────────────────────────────────────────

@allure.feature("Data / AI Response Quality")
@allure.story("Cross-Language Consistency")
@pytest.mark.ai_validation
class TestCrossLanguageConsistency(BaseTest):

    @allure.title("[TC_DATA_CONS_001] EN vs AR Emirates ID renewal gives consistent answers")
    @allure.severity(allure.severity_level.NORMAL)
    def test_TC_DATA_CONS_001_en_ar_consistency(
        self,
        chatbot_page: ChatbotPage,
        ai_validator: AIValidator,
        settings: Settings,
    ) -> None:
        """
        Send 'How do I renew my Emirates ID?' in English.
        Send 'كيف أجدد هويتي الإماراتية؟' in Arabic (fresh session).
        The two responses must be semantically consistent.
        Cosine similarity between the two response embeddings must be >= 0.55.

        Uses the shared multilingual embedding space — Arabic and English
        responses about the same topic cluster near each other.
        """
        tc = _DATA_TESTS["TC_DATA_CONS_001"]

        if not settings.should_run_english():
            pytest.skip("English tests disabled — needed for consistency check")
        if not settings.should_run_arabic():
            pytest.skip("Arabic tests disabled — needed for consistency check")

        # ── English leg ───────────────────────────────────────────────────────
        with allure.step(f"Send English prompt: {tc['prompt_en']}"):
            response_en = self.send_and_capture(chatbot_page, tc["prompt_en"])
            self.assert_response_not_empty(response_en)

        # ── Arabic leg (navigate to AR URL) ───────────────────────────────────
        with allure.step("Open a fresh Arabic session"):
            chatbot_page.driver.get("https://beta-ask.u.ae/ar/uask")
            chatbot_page.wait_for_page_ready()
            chatbot_page._wait_for_angular_bootstrap()
            chatbot_page._activate_widget_if_needed()

        with allure.step(f"Send Arabic prompt: {tc['prompt_ar']}"):
            response_ar = self.send_and_capture(chatbot_page, tc["prompt_ar"])
            self.assert_response_not_empty(response_ar)

        # ── Cross-language similarity ──────────────────────────────────────────
        with allure.step("Compute cross-language similarity between EN and AR responses"):
            score = ai_validator.compare_responses(response_en, response_ar)
            self.attach_text(
                f"EN response : {response_en[:300]}\n\n"
                f"AR response : {response_ar[:300]}\n\n"
                f"Similarity  : {score:.4f}\n"
                f"Min required: {tc['min_cross_similarity']}",
                name="Cross-Language Consistency Report",
            )
            assert score >= tc["min_cross_similarity"], (
                f"[TC_DATA_CONS_001] Cross-language consistency score {score:.4f} "
                f"is below minimum {tc['min_cross_similarity']}.\n"
                f"The EN and AR responses do not cover the same topic."
            )


# ─────────────────────────────────────────────────────────────────────────────
# TC_DATA_EDGE_001  &  TC_DATA_EDGE_002   Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

@allure.feature("Data / AI Response Quality")
@allure.story("Edge Cases")
@pytest.mark.ai_validation
class TestEdgeCases(BaseTest):

    @allure.title("[TC_DATA_EDGE_001] Gibberish input — bot responds gracefully")
    @allure.severity(allure.severity_level.NORMAL)
    def test_TC_DATA_EDGE_001_gibberish_fallback(
        self,
        chatbot_page: ChatbotPage,
        ai_validator: AIValidator,
    ) -> None:
        """
        Send pure gibberish: 'aaaaaaaaa bbbbbbb 12312312 xyzxyzxyz'.
        The bot must:
          1. Not crash or return a raw HTTP 500 / stack trace
          2. Return a non-empty response (a polite clarification or fallback)
          3. Not echo back any forbidden error patterns
        """
        tc = _DATA_TESTS["TC_DATA_EDGE_001"]

        with allure.step(f"Send gibberish prompt: {tc['prompt']!r}"):
            response = self.send_and_capture(chatbot_page, tc["prompt"])

        with allure.step("Assert response is not empty (no crash)"):
            self.assert_response_not_empty(response)

        with allure.step("Assert no raw error messages or stack traces"):
            self.assert_no_forbidden_content(response, tc["forbidden_patterns"])

        self.attach_prompt_response(
            prompt=tc["prompt"],
            response=response,
            language="en",
        )

    @allure.title("[TC_DATA_EDGE_002] Repeated question gives consistent answers")
    @allure.severity(allure.severity_level.NORMAL)
    def test_TC_DATA_EDGE_002_repeat_question_consistency(
        self,
        chatbot_page: ChatbotPage,
        ai_validator: AIValidator,
        settings: Settings,
    ) -> None:
        """
        Ask 'What can you help me with?' twice in the same session.
        Both responses must:
          1. Be non-empty
          2. Contain at least one expected keyword
          3. Have cosine similarity >= 0.65 with each other
             (same intent should yield semantically consistent answers)
        """
        if not settings.should_run_english():
            pytest.skip("English tests disabled via TEST_LANGUAGE setting")

        tc = _DATA_TESTS["TC_DATA_EDGE_002"]
        prompt = tc["prompt"]

        with allure.step(f"First send: {prompt!r}"):
            response_1 = self.send_and_capture(chatbot_page, prompt)
            self.assert_response_not_empty(response_1)

        with allure.step(f"Second send (same prompt): {prompt!r}"):
            response_2 = self.send_and_capture(chatbot_page, prompt)
            self.assert_response_not_empty(response_2)

        with allure.step("Compute similarity between response 1 and response 2"):
            score = ai_validator.compare_responses(response_1, response_2)
            self.attach_text(
                f"Response 1  : {response_1[:300]}\n\n"
                f"Response 2  : {response_2[:300]}\n\n"
                f"Similarity  : {score:.4f}\n"
                f"Min required: {tc['min_repeat_similarity']}",
                name="Repeat Consistency Report",
            )
            assert score >= tc["min_repeat_similarity"], (
                f"[TC_DATA_EDGE_002] Repeat consistency score {score:.4f} is below "
                f"minimum {tc['min_repeat_similarity']}.\n"
                f"The same question returned very different answers."
            )

        with allure.step(f"Assert keywords present in both responses: {tc['expected_keywords']}"):
            if tc["expected_keywords"]:
                self.assert_response_contains_keyword(response_1, tc["expected_keywords"])
                self.assert_response_contains_keyword(response_2, tc["expected_keywords"])
