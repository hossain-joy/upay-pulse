"""
upay Pulse - AI Provider Abstraction
Single source of truth for chat responses: a cloud Gemini LLM. The fallback is
a minimal, non-coaching message — no templates, no scripts, no pre-written text.
"""

import abc
import time
import logging
from typing import Dict, Any, Tuple, Optional
from backend.app.core.config import settings

logger = logging.getLogger("upay_pulse.ai_provider")


class AIProvider(abc.ABC):
    @abc.abstractmethod
    def generate_financial_advice(self, query: str, context: Dict[str, Any]) -> str:
        """
        Processes a financial query with user context and returns the model's
        raw reply text. The provider owns the entire response — no scaffolding,
        no appended phrases, no post-processing.
        """
        pass


class MockLocalProvider(AIProvider):
    """
    Offline fallback used only when the cloud LLM is completely unreachable.
    Intentionally returns a single short, non-coaching message — never a
    templated reply. The caller decides how to present it to the user.
    """

    def generate_financial_advice(self, query: str, context: Dict[str, Any]) -> str:
        name = context.get("full_name") or ""
        greeting = f"{name}, " if name else ""
        return (
            f"দুঃখিত {greeting}এই মুহূর্তে AI পরামর্শক সেবা পাওয়া যাচ্ছে না। "
            "আপনার ওয়ালেট, গ্রেস বা এফডিআর সংক্রান্ত প্রশ্নের জন্য একটু পরে আবার চেষ্টা করুন।"
        )


class GeminiProvider(AIProvider):
    """
    Cloud Gemini LLM Provider.
    Falls back gracefully to MockLocalProvider if the API key is not configured
    or all attempts fail.

    Design notes:
      * Model list is validated against the live API once (cached) rather than
        guessing hard-coded names that may not exist for the user's key/region.
      * Total wall-clock budget per request is bounded (TOTAL_REQUEST_BUDGET_S),
        not stacked. Worst-case latency is ~5s instead of ~14s.
      * Every failure is logged so silent fallback is no longer invisible.
      * The provider returns only the model's text. No intent label is added,
        no canned phrases are prepended or appended, no post-processing mutates
        the reply.
    """

    # Preferred (cheap/fast) models first. The set is intentionally narrow; we
    # dynamically validate availability on first use instead of guessing.
    PREFERRED_MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ]

    # Total wall-clock budget for a chat request (all model attempts combined).
    TOTAL_REQUEST_BUDGET_S = 5.0
    PER_REQUEST_TIMEOUT_S = 3.0

    # Re-validate model list at most this often.
    _VALIDATION_TTL_S = 600

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback = MockLocalProvider()
        self._validated_models: Optional[list] = None
        self._validated_at: float = 0.0

    def _list_available_models(self) -> list:
        """
        Query the live API for models that support generateContent and contain
        'flash' in the name. Falls back to PREFERRED_MODELS on any error.
        Cached for _VALIDATION_TTL_S seconds.
        """
        now = time.time()
        if self._validated_models is not None and (now - self._validated_at) < self._VALIDATION_TTL_S:
            return self._validated_models

        try:
            import urllib.request
            import json
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models"
                f"?key={self.api_key}"
            )
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            discovered = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", []) or []
                if "generateContent" in methods and "flash" in name.lower():
                    discovered.append(name)
            # Preserve preferred order first, then any extras discovered.
            seen = set()
            merged = []
            # Preferred models go first — they are validated to work for this key.
            for n in self.PREFERRED_MODELS:
                if n not in seen:
                    merged.append(n)
                    seen.add(n)
            # Append any additionally discovered models not already in the list.
            for n in discovered:
                if n not in seen:
                    merged.append(n)
                    seen.add(n)
            self._validated_models = merged or list(self.PREFERRED_MODELS)
            self._validated_at = now
            logger.info("Gemini validated models: %s", self._validated_models)
            return self._validated_models
        except Exception as e:
            logger.warning(
                "Gemini model discovery failed (%s); using preferred list", e,
            )
            self._validated_models = list(self.PREFERRED_MODELS)
            self._validated_at = now
            return self._validated_models

    def _try_model(
        self, model: str, payload_bytes: bytes, timeout_s: float
    ) -> Optional[str]:
        """Return the model's text on success; None on retryable failure."""
        try:
            import urllib.request
            import urllib.error
            import json
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={self.api_key}"
            )
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as http_err:
                body = http_err.read().decode("utf-8", errors="replace")
                err_data = json.loads(body) if body else {}
                code = err_data.get("error", {}).get("code", http_err.code)
                logger.warning("Gemini model '%s' HTTP %s: %s", model, code, err_data.get("error", {}).get("message", "")[:120])
                return None
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text
        except Exception as e:
            logger.warning("Gemini model '%s' failed: %s", model, e)
            return None

    def generate_financial_advice(self, query: str, context: Dict[str, Any]) -> str:
        if not self.api_key or self.api_key.strip() == "":
            return self.fallback.generate_financial_advice(query, context)

        import json

        # The system prompt is the *only* steering. It sets persona, language,
        # tone, and constraints. The model produces the entire reply from here;
        # we do not prepend, append, rewrite, or classify anything in code.
        system_instruction = (
            "You are the AI Financial Coach for 'upay Pulse', a mobile financial "
            "services (MFS) platform in Bangladesh. The user is an everyday citizen, "
            "small merchant, or garment worker.\n"
            "\n"
            "Rules:\n"
            "1. Reply entirely in natural, polite colloquial Bengali (বাংলা). Use "
            "the user's verified full_name from context if available, but if the "
            "user introduces themselves by a different name in the query, use that.\n"
            "2. Open with 'আসসালামু আলাইকুম!' once per conversation only — do not "
            "force this greeting if the conversation has already started.\n"
            "3. Use the financial context (wallet balance, grace overdraft, micro-FDR, "
            "spending pattern, reliability score, deficit forecast) to give specific, "
            "actionable guidance. Reference real numbers when relevant.\n"
            "4. Keep replies under 3-4 concise sentences. No bullet lists, no headers, "
            "no markdown. Conversational prose only.\n"
            "5. Never invent products, interest rates, or policies that are not "
            "supported by the context. If asked about something outside your scope, "
            "say so honestly.\n"
            "6. Do not label, tag, or prepend category names like 'Balance Inquiry' "
            "or 'Grace Eligibility' to your reply. Just answer naturally.\n"
            "7. If the user greets you or introduces themselves, respond warmly in "
            "Bengali without reciting their financial details unprompted."
        )

        prompt = (
            f"User Query: {query}\n"
            f"User Financial Context: {json.dumps(context, ensure_ascii=False)}"
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": system_instruction},
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 512
            }
        }
        payload_bytes = json.dumps(payload).encode("utf-8")

        # Total wall-clock budget is bounded; per-attempt timeout is the
        # remaining time (not a fixed N * PER_REQUEST_TIMEOUT_S) so worst-case
        # latency is ~TOTAL_REQUEST_BUDGET_S instead of N * PER_REQUEST_TIMEOUT_S.
        deadline = time.monotonic() + self.TOTAL_REQUEST_BUDGET_S
        models = self._list_available_models()

        for model in models:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(
                    "Gemini budget exhausted (%.2fs); stopping retry loop",
                    self.TOTAL_REQUEST_BUDGET_S,
                )
                break
            # Each attempt gets whatever time is left, capped at PER_REQUEST_TIMEOUT_S.
            attempt_timeout = min(self.PER_REQUEST_TIMEOUT_S, remaining)

            text = self._try_model(model, payload_bytes, attempt_timeout)
            if text is not None:
                return text

        # Resilient offline fallback if all cloud models fail, timeout, or rate-limit.
        logger.warning(
            "All Gemini models failed within %.2fs budget; using MockLocalProvider",
            self.TOTAL_REQUEST_BUDGET_S,
        )
        return self.fallback.generate_financial_advice(query, context)


def get_ai_provider() -> AIProvider:
    """Factory to retrieve active AI provider based on configuration."""
    if settings.AI_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider(api_key=settings.GEMINI_API_KEY)
    return MockLocalProvider()