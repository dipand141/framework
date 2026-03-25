"""
utils/ai_validator.py
─────────────────────
AI-powered response validation engine.

Uses sentence-transformers to compute semantic similarity between
chatbot responses and expected concepts. Also detects:
  - Hallucinated / off-topic responses (low similarity to expected concepts)
  - Forbidden content patterns (regex / substring matching)
  - Language consistency (response language matches prompt language)
  - Response quality (completeness, no broken HTML, minimum length)

Model: paraphrase-multilingual-MiniLM-L12-v2
  - 118 MB, fast CPU inference
  - Shared embedding space for EN + AR → cross-language comparison works
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

import allure
import numpy as np

from utils.logger import get_logger

log = get_logger(__name__)


# ── Data classes ────────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Structured result returned by AIValidator.validate_response()."""

    passed: bool
    max_similarity_score: float
    similarity_scores: List[float]
    forbidden_violations: List[str]
    language_match: Optional[bool]   # None = language detection not available
    quality_issues: List[str]
    details: str

    def to_report_text(
        self,
        prompt: str = "",
        response: str = "",
        language: str = "",
    ) -> str:
        status = "PASS ✓" if self.passed else "FAIL ✗"
        lines = [
            "═" * 60,
            f"  AI VALIDATION REPORT  –  {status}",
            "═" * 60,
            f"  Language  : {language or 'unknown'}",
            f"  Prompt    : {prompt[:120]}",
            f"  Response  : {response[:300]}{'…' if len(response) > 300 else ''}",
            "─" * 60,
            f"  Max Sim.  : {self.max_similarity_score:.4f}",
            f"  Scores    : {[f'{s:.4f}' for s in self.similarity_scores]}",
            f"  Lang Match: {self.language_match}",
        ]
        if self.forbidden_violations:
            lines.append(f"  FORBIDDEN : {self.forbidden_violations}")
        if self.quality_issues:
            lines.append(f"  QUALITY   : {self.quality_issues}")
        lines += ["─" * 60, f"  Notes     : {self.details}", "═" * 60]
        return "\n".join(lines)


# ── Validator ───────────────────────────────────────────────────────────────


class AIValidator:
    """
    Semantic similarity engine for validating chatbot responses.
    Instantiate once at session scope; the model load is expensive (~2–5 s).
    """

    # Patterns that always indicate poor / unsafe response quality
    _ALWAYS_FORBIDDEN: List[str] = [
        r"<script[\s>]",
        r"javascript\s*:",
        r"onerror\s*=",
        r"onload\s*=",
        r"eval\s*\(",
        r"DROP\s+TABLE",
        r"\{\{.*\}\}",        # template injection echo
    ]

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        threshold: float = 0.65,
    ) -> None:
        self.threshold = threshold
        self.model_name = model_name
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            log.info("Loading sentence-transformer model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            log.info("Model loaded successfully.")
        except ImportError:
            log.error(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            )
        except Exception as exc:
            log.error("Failed to load model '%s': %s", self.model_name, exc)

    # ── Core API ──────────────────────────────────────────────────────────────

    def validate_response(
        self,
        response: str,
        expected_concepts: List[str],
        forbidden_patterns: Optional[List[str]] = None,
        prompt: str = "",
        language: str = "",
        attach_to_allure: bool = True,
    ) -> ValidationResult:
        """
        Validate a chatbot response against expected concepts and forbidden patterns.

        Returns a ValidationResult dataclass.
        """
        if not response:
            result = ValidationResult(
                passed=False,
                max_similarity_score=0.0,
                similarity_scores=[],
                forbidden_violations=["Response is empty"],
                language_match=None,
                quality_issues=["Empty response"],
                details="No response text received from chatbot.",
            )
            if attach_to_allure:
                self._attach_report(result, prompt, response, language)
            return result

        # 1. Check forbidden patterns
        all_forbidden = list(self._ALWAYS_FORBIDDEN) + (forbidden_patterns or [])
        violations = self._check_forbidden(response, all_forbidden)

        # 2. Compute semantic similarity
        scores = self._compute_similarity_scores(response, expected_concepts)
        max_score = max(scores) if scores else 0.0

        # 3. Language consistency
        lang_match = self._check_language_consistency(response, language)

        # 4. Quality checks
        quality_issues = self._check_quality(response)

        # 5. Overall pass/fail
        # Fail conditions: any forbidden violation, score below threshold (if concepts given), critical quality issue
        passed = (
            len(violations) == 0
            and (len(expected_concepts) == 0 or max_score >= self.threshold)
            and "incomplete_html" not in quality_issues
        )

        hallucination_flag = (
            len(expected_concepts) > 0
            and max_score < self.threshold
            and max_score < 0.40
        )
        details = (
            "Potential hallucination detected – response is off-topic."
            if hallucination_flag
            else ("Validation passed." if passed else "Validation failed – see details.")
        )

        result = ValidationResult(
            passed=passed,
            max_similarity_score=max_score,
            similarity_scores=scores,
            forbidden_violations=violations,
            language_match=lang_match,
            quality_issues=quality_issues,
            details=details,
        )

        if attach_to_allure:
            self._attach_report(result, prompt, response, language)

        log.info(
            "Validation %s | score=%.3f threshold=%.3f violations=%d",
            "PASS" if passed else "FAIL",
            max_score,
            self.threshold,
            len(violations),
        )
        return result

    # ── Similarity ────────────────────────────────────────────────────────────

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """
        Compute cosine similarity between two texts.
        Returns a float in [0, 1].
        """
        if self._model is None:
            log.warning("Model not loaded – returning 0.0 similarity")
            return 0.0

        from sklearn.metrics.pairwise import cosine_similarity

        embeddings = self._model.encode([text_a, text_b], convert_to_numpy=True)
        score = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
        # Clamp to [0, 1] (cosine can be slightly negative for orthogonal vectors)
        return max(0.0, min(1.0, score))

    def _compute_similarity_scores(
        self, response: str, concepts: List[str]
    ) -> List[float]:
        """Return a similarity score for each expected concept."""
        if not concepts or self._model is None:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        all_texts = [response] + concepts
        embeddings = self._model.encode(all_texts, convert_to_numpy=True)
        response_emb = embeddings[0:1]
        concept_embs = embeddings[1:]

        scores = cosine_similarity(response_emb, concept_embs)[0]
        return [max(0.0, float(s)) for s in scores]

    # ── Forbidden patterns ────────────────────────────────────────────────────

    def _check_forbidden(self, response: str, patterns: List[str]) -> List[str]:
        """Return list of forbidden patterns that were found in the response."""
        violations = []
        for pattern in patterns:
            if re.search(pattern, response, re.IGNORECASE | re.DOTALL):
                violations.append(pattern)
        return violations

    # ── Language consistency ──────────────────────────────────────────────────

    def _check_language_consistency(
        self, response: str, expected_language: str
    ) -> Optional[bool]:
        """
        Returns True if the detected response language matches expected_language.
        Returns None if langdetect is not available or language is ambiguous.
        """
        if not expected_language or expected_language == "cross":
            return None

        try:
            from langdetect import LangDetectException, detect

            detected = detect(response)
            # Map common Arabic dialect codes to 'ar'
            if detected.startswith("ar"):
                detected = "ar"
            match = detected == expected_language.lower()
            if not match:
                log.warning(
                    "Language mismatch: expected=%s detected=%s",
                    expected_language,
                    detected,
                )
            return match
        except Exception:
            return None

    # ── Quality checks ────────────────────────────────────────────────────────

    def _check_quality(self, response: str) -> List[str]:
        """
        Non-semantic quality heuristics:
          - Response is too short (< 10 chars after stripping)
          - Contains raw unescaped HTML tags (broken rendering)
          - Appears to be an incomplete thought (ends mid-sentence without punctuation)
        """
        issues = []
        clean = response.strip()

        if len(clean) < 10:
            issues.append("too_short")

        # Detect unescaped / raw HTML in the response text
        if re.search(r"<[a-z]{1,10}(\s[^>]*)?>", clean, re.IGNORECASE):
            issues.append("incomplete_html")

        # Detect suspicious abrupt endings (no terminal punctuation, common in truncation)
        stripped_end = clean.rstrip()
        if len(stripped_end) > 30:
            last_char = stripped_end[-1]
            if last_char not in ".!?،؟…\"'":
                # Only flag if it ends with a mid-word character
                if stripped_end[-1].isalpha():
                    issues.append("potentially_truncated")

        return issues

    # ── Allure attachment ─────────────────────────────────────────────────────

    @staticmethod
    def _attach_report(
        result: ValidationResult,
        prompt: str,
        response: str,
        language: str,
    ) -> None:
        try:
            report_text = result.to_report_text(
                prompt=prompt, response=response, language=language
            )
            allure.attach(
                report_text,
                name="AI Validation Report",
                attachment_type=allure.attachment_type.TEXT,
            )
        except Exception:
            pass  # Never let reporting failure break a test

    # ── Convenience ──────────────────────────────────────────────────────────

    def is_response_relevant(
        self, response: str, concepts: List[str], threshold: Optional[float] = None
    ) -> bool:
        """Quick True/False relevance check without a full ValidationResult."""
        t = threshold if threshold is not None else self.threshold
        scores = self._compute_similarity_scores(response, concepts)
        return bool(scores) and max(scores) >= t

    def compare_responses(self, response_a: str, response_b: str) -> float:
        """
        Compare two chatbot responses for consistency (e.g., EN vs AR for same intent).
        Returns cosine similarity score.
        """
        score = self.compute_similarity(response_a, response_b)
        log.info("Response consistency score: %.4f", score)
        return score
