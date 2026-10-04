"""
upay Pulse - AI Provider Abstraction
Provides pluggable AI interfaces: Gemini AI (Cloud LLM) and MockLocalProvider (Deterministic Offline Fallback).
Guarantees resilient, low-latency, dialect-aware Bengali financial coaching without internet dependency.
"""

import abc
import re
import time
import logging
from typing import Dict, Any, Tuple, Optional
from backend.app.core.config import settings

logger = logging.getLogger("upay_pulse.ai_provider")

class AIProvider(abc.ABC):
    @abc.abstractmethod
    def generate_financial_advice(self, query: str, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        Processes financial query with user context.
        Returns: (response_bangla_text, detected_intent)
        """
        pass

class MockLocalProvider(AIProvider):
    """
    Zero-network local fallback LLM provider.
    Interprets Bengali and English queries, identifies financial intent,
    and returns contextually grounded responses referencing real wallet metrics.
    """

    def generate_financial_advice(self, query: str, context: Dict[str, Any]) -> Tuple[str, str]:
        q = query.lower().strip()
        balance = float(context.get("wallet_balance", 0.0))
        grace_balance = float(context.get("grace_balance", 0.0))
        grace_limit = float(context.get("approved_grace_limit", 50.0))
        spending_pattern = context.get("spending_pattern", "নিত্যপ্রয়োজনীয় খরচ ও ইউটিলিটি বিল")
        has_deficit = context.get("has_deficit_alert", False)
        deficit_date = context.get("deficit_date", "আগামী সপ্তাহে")
        idle_deposit = round(max(100.0, balance * 0.40), 2)

        # 1. Balance Inquiry
        if any(w in q for w in ["ব্যালেন্স", "টাকা আছে", "কত টাকা", "balance", "balance koto", "koto ache"]):
            intent = "BALANCE_INQUIRY"
            response = (
                f"আপনার উপায় ওয়ালেটে বর্তমান ব্যালেন্স রয়েছে ৳{balance:,.2f} টাকা। "
                f"আপনার এই ব্যালেন্সের মধ্যে ৳{idle_deposit:,.2f} টাকা একটি মাইক্রো-এফডিআরে জমা করলে আপনি ৮.৫০% পর্যন্ত অতিরিক্ত মুনাফা পেতে পারেন।"
            )

        # 2. Deficit Alert or Upcoming Bill Payment
        elif any(w in q for w in ["বিল", "বাকি", "ঘাটতি", "খরচ হবে", "bill", "deficit", "baki"]):
            intent = "DEFICIT_ALERT"
            if has_deficit:
                response = (
                    f"সতর্কতা! আপনার খরচের গতিধারা অনুযায়ী {deficit_date}-এর মধ্যে অ্যাকাউন্টে সম্ভাব্য ঘাটতি দেখা দিতে পারে। "
                    f"বিল ও জরুরি খরচ নির্বিঘ্ন রাখতে আপনার উপায় গ্রেস থেকে ৳{grace_limit:.0f} ওভারড্রাফট নিতে পারেন অথবা নিকটস্থ এজেন্ট থেকে ক্যাশ-ইন করে নিন।"
                )
            else:
                response = (
                    f"আপনার আগামী ১৫ দিনের মধ্যে বড় কোনো বিলের ঝুঁকিপূর্ণ ঘাটতি নেই। "
                    f"আপনার সাম্প্রতিক মাসিক ব্যয়ের ধরন: {spending_pattern}। নিয়মিত হিসাব রাখতে উপায় পালস সক্রিয় রয়েছে।"
                )

        # 3. upay Grace Micro-Overdraft Loan
        elif any(w in q for w in ["গ্রেস", "লোন", "ধার", "ধার নেওয়া", "জরুরি টাকা", "grace", "loan", "overdraft"]):
            intent = "GRACE_ELIGIBILITY"
            if grace_balance > 0:
                response = (
                    f"আপনার বর্তমানে ৳{grace_balance:.2f} টাকার উপায় গ্রেস ওভারড্রাফট সক্রিয় রয়েছে। "
                    f"আপনার পরবর্তী এজেন্ট ক্যাশ-ইনের সময় এই টাকা কোনো বাড়তি চার্জ ছাড়াই স্বয়ংক্রিয়ভাবে সমন্বয় করা হবে।"
                )
            else:
                response = (
                    f"অভিনন্দন! আপনার ভালো লেনদেন রেকর্ডের জন্য আপনি সর্বোচ্চ ৳{grace_limit:.2f} টাকা পর্যন্ত উপায় গ্রেস (upay Grace) "
                    f"জরুরি ওভারড্রাফট সুবিধা পেতে পারেন। কোনো অতিরিক্ত সুদ ছাড়াই জরুরি বিল বা টাকা পাঠাতে এটি ব্যবহার করুন।"
                )

        # 4. Micro-FDR / Savings Opportunities
        elif any(w in q for w in ["এফডিআর", "সঞ্চয়", "ডিপিএস", "লাভ", "মুনাফা", "fdr", "saving", "deposit", "profit"]):
            intent = "MICRO_FDR"
            response = (
                f"উপায় মাইক্রো-এফডিআরে আপনার অলস টাকার ওপর আকর্ষণীয় মুনাফা অর্জন করুন! "
                f"৭ দিনের জন্য ৬.৫০%, ৩০ দিনের জন্য ৭.৫০% এবং ৯০ দিনের জন্য ৮.৫০% বার্ষিক হারে মুনাফা পাওয়া যায়। "
                f"আপনার ওয়ালেটের ৳{idle_deposit:.2f} দিয়ে আজই একটি নিরাপদ মাইক্রো-এফডিআর শুরু করতে পারেন।"
            )

        # 5. Spending Insights & Habits
        elif any(w in q for w in ["কোথায় খরচ", "খরচ বেশি", "হিসাব", "spending", "khoroch", "insight"]):
            intent = "SPENDING_INSIGHT"
            response = (
                f"আপনার ব্যয়ের বিশ্লেষণ অনুযায়ী, আপনার অধিকাংশ লেনদেন হয়েছে '{spending_pattern}' খাতে। "
                f"আপনার ভবিষ্যৎ নিরাপত্তার জন্য প্রতি মাসের উপার্জনের কমপক্ষে ১০-১৫% সঞ্চয় আলাদা রাখার পরামর্শ দিচ্ছি।"
            )

        # 6. General Conversational Fallback
        else:
            intent = "GENERAL_GUIDE"
            response = (
                f"আসসালামু আলাইকুম! আমি উপায় পালস ডিজিটাল আর্থিক পরামর্শক। আপনার অ্যাকাউন্টে ব্যালেন্স ৳{balance:.2f} টাকা। "
                f"আপনি আমাকে ব্যালেন্স পরীক্ষা, উপায় গ্রেস লোন, মাইক্রো-এফডিআর সঞ্চয় অথবা আসন্ন বিল সংক্রান্ত যেকোনো প্রশ্ন করতে পারেন।"
            )

        return response, intent

class GeminiProvider(AIProvider):
    """
    Cloud Gemini LLM Provider.
    Falls back gracefully to MockLocalProvider if API key is not configured or network fails.

    Design notes:
      * Model list is validated against the live API once (cached) rather than
        guessing 4 hard-coded names that may not exist for the user's key/region.
      * Total wall-clock budget per request is bounded (TOTAL_REQUEST_BUDGET_S),
        not stacked. Worst-case latency is now ~5s instead of ~14s.
      * Every failure is logged so silent fallback is no longer invisible.
    """

    # Preferred (cheap/fast) models first. The set is intentionally narrow; we
    # dynamically validate availability on first use instead of guessing.
    PREFERRED_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
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
            # Preserve preferred order, then any extras discovered.
            seen = set()
            merged = []
            for n in self.PREFERRED_MODELS + discovered:
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

    @staticmethod
    def _classify_intent(query: str) -> str:
        q_low = query.lower()
        if any(w in q_low for w in ["ব্যালেন্স", "টাকা আছে", "balance"]):
            return "BALANCE_INQUIRY"
        if any(w in q_low for w in ["বিল", "বাকি", "ঘাটতি", "bill"]):
            return "DEFICIT_ALERT"
        if any(w in q_low for w in ["গ্রেস", "লোন", "ধার", "grace", "loan"]):
            return "GRACE_ELIGIBILITY"
        if any(w in q_low for w in ["এফডিআর", "সঞ্চয়", "fdr", "saving"]):
            return "MICRO_FDR"
        if any(w in q_low for w in ["কোথায় খরচ", "খরচ বেশি", "spending"]):
            return "SPENDING_INSIGHT"
        return "GENERAL_GUIDE"

    def _try_model(
        self, model: str, payload_bytes: bytes, timeout_s: float
    ) -> Optional[str]:
        """Return the model's text on success; None on retryable failure."""
        try:
            import urllib.request
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
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text
        except Exception as e:
            logger.warning("Gemini model '%s' failed: %s", model, e)
            return None

    def generate_financial_advice(self, query: str, context: Dict[str, Any]) -> Tuple[str, str]:
        if not self.api_key or self.api_key.strip() == "":
            return self.fallback.generate_financial_advice(query, context)

        import urllib.request  # noqa: F401  (kept for backwards imports)
        import json

        system_instruction = (
            "You are the empathetic, culturally aware, dialect-sensitive AI Financial Coach for 'upay Pulse' Mobile Financial Services (MFS) in Bangladesh. "
            "The user is an everyday citizen, small merchant, or garment worker. "
            "Always reply in natural, friendly, polite colloquial Bengali (বাংলা), starting with 'আসসালামু আলাইকুম!'. "
            "Reference the user's real financial context provided (wallet balance, grace overdraft, micro-FDR, and spending patterns). "
            "Offer actionable tips on managing balance, preventing cash-flow deficits, utilizing 'upay Grace' micro-overdrafts, or opening Micro-FDRs. "
            "Keep responses under 3-4 concise sentences."
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
                "temperature": 0.3,
                "maxOutputTokens": 1024
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
                return text, self._classify_intent(query)

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