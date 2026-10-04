"""
upay Pulse - AI Provider Abstraction
Provides pluggable AI interfaces: Gemini AI (Cloud LLM) and MockLocalProvider (Deterministic Offline Fallback).
Guarantees resilient, low-latency, dialect-aware Bengali financial coaching without internet dependency.
"""

import abc
import re
import time
from typing import Dict, Any, Tuple, Optional
from backend.app.core.config import settings

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
        spending_pattern = context.get("spending_pattern", "নিত্যপ্রয়োজনীয় খরচ ও ইউটিলিটি বিল")
        has_deficit = context.get("has_deficit_alert", False)
        deficit_date = context.get("deficit_date", "আগামী সপ্তাহে")
        idle_deposit = round(max(100.0, balance * 0.40), 2)

        # 1. Balance Inquiry
        if any(w in q for w in ["ব্যালেন্স", "টাকা আছে", "কত টাকা", "balance", "balance koto", "koto ache"]):
            intent = "BALANCE_INQUIRY"
            response = (
                f"আপনার উপায় ওয়ালেটে বর্তমান ব্যালেন্স রয়েছে ৳{balance:,.2f} টাকা। "
                f"আপনার এই ব্যালেন্সের মধ্যে ৳{idle_deposit:,.2f} টাকা একটি মাইক্রো-এফডিআরে জমা করলে আপনি ৮.৫০% পর্যন্ত অতিরিক্ত মুনাফা পেতে পারেন।"
            )

        # 2. Deficit Alert or Upcoming Bill Payment
        elif any(w in q for w in ["বিল", "বাকি", "ঘাটতি", "খরচ হবে", "bill", "deficit", "baki"]):
            intent = "DEFICIT_ALERT"
            if has_deficit:
                response = (
                    f"সতর্কতা! আপনার খরচের গতিধারা অনুযায়ী {deficit_date}-এর মধ্যে অ্যাকাউন্টে সম্ভাব্য ঘাটতি দেখা দিতে পারে। "
                    f"বিল ও জরুরি খরচ নির্বিঘ্ন রাখতে আপনার উপায় গ্রেস থেকে ৳{grace_limit:.0f} ওভারড্রাফট নিতে পারেন অথবা নিকটস্থ এজেন্ট থেকে ক্যাশ-ইন করে নিন।"
                )
            else:
                response = (
                    f"আপনার আগামী ১৫ দিনের মধ্যে বড় কোনো বিলের ঝুঁকিপূর্ণ ঘাটতি নেই। "
                    f"আপনার সাম্প্রতিক মাসিক ব্যয়ের ধরন: {spending_pattern}। নিয়মিত হিসাব রাখতে উপায় পালস সক্রিয় রয়েছে।"
                )

        # 3. upay Grace Micro-Overdraft Loan
        elif any(w in q for w in ["গ্রেস", "লোন", "ধার", "ধার নেওয়া", "জরুরি টাকা", "grace", "loan", "overdraft"]):
            intent = "GRACE_ELIGIBILITY"
            if grace_balance > 0:
                response = (
                    f"আপনার বর্তমানে ৳{grace_balance:.2f} টাকার উপায় গ্রেস ওভারড্রাফট সক্রিয় রয়েছে। "
                    f"আপনার পরবর্তী এজেন্ট ক্যাশ-ইনের সময় এই টাকা কোনো বাড়তি চার্জ ছাড়াই স্বয়ংক্রিয়ভাবে সমন্বয় করা হবে।"
                )
            else:
                response = (
                    f"অভিনন্দন! আপনার ভালো লেনদেন রেকর্ডের জন্য আপনি সর্বোচ্চ ৳{grace_limit:.2f} টাকা পর্যন্ত উপায় গ্রেস (upay Grace) "
                    f"জরুরি ওভারড্রাফট সুবিধা পেতে পারেন। কোনো অতিরিক্ত সুদ ছাড়াই জরুরি বিল বা টাকা পাঠাতে এটি ব্যবহার করুন।"
                )

        # 4. Micro-FDR / Savings Opportunities
        elif any(w in q for w in ["এফডিআর", "সঞ্চয়", "ডিপিএস", "লাভ", "মুনাফা", "fdr", "saving", "deposit", "profit"]):
            intent = "MICRO_FDR"
            response = (
                f"উপায় মাইক্রো-এফডিআরে আপনার অলস টাকার ওপর আকর্ষণীয় মুনাফা অর্জন করুন! "
                f"৭ দিনের জন্য ৬.৫০%, ৩০ দিনের জন্য ৭.৫০% এবং ৯০ দিনের জন্য ৮.৫০% বার্ষিক হারে মুনাফা পাওয়া যায়। "
                f"আপনার ওয়ালেটের ৳{idle_deposit:.2f} দিয়ে আজই একটি নিরাপদ মাইক্রো-এফডিআর শুরু করতে পারেন।"
            )

        # 5. Spending Insights & Habits
        elif any(w in q for w in ["কোথায় খরচ", "খরচ বেশি", "হিসাব", "spending", "khoroch", "insight"]):
            intent = "SPENDING_INSIGHT"
            response = (
                f"আপনার ব্যয়ের বিশ্লেষণ অনুযায়ী, আপনার অধিকাংশ লেনদেন হয়েছে '{spending_pattern}' খাতে। "
                f"আপনার ভবিষ্যৎ নিরাপত্তার জন্য প্রতি মাসের উপার্জনের কমপক্ষে ১০-১৫% সঞ্চয় আলাদা রাখার পরামর্শ দিচ্ছি।"
            )

        # 6. General Conversational Fallback
        else:
            intent = "GENERAL_GUIDE"
            response = (
                f"নমস্কার! আমি উপায় পালস ডিজিটাল আর্থিক পরামর্শক। আপনার অ্যাকাউন্টে ব্যালেন্স ৳{balance:.2f} টাকা। "
                f"আপনি আমাকে ব্যালেন্স পরীক্ষা, উপায় গ্রেস লোন, মাইক্রো-এফডিআর সঞ্চয় অথবা আসন্ন বিল সংক্রান্ত যেকোনো প্রশ্ন করতে পারেন।"
            )

        return response, intent

class GeminiProvider(AIProvider):
    """
    Cloud Gemini LLM Provider.
    Falls back gracefully to MockLocalProvider if API key is not configured or network fails.
    """

    CANDIDATE_MODELS = [
        "gemini-flash-lite-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-flash-latest"
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.fallback = MockLocalProvider()

    def generate_financial_advice(self, query: str, context: Dict[str, Any]) -> Tuple[str, str]:
        if not self.api_key or self.api_key.strip() == "":
            return self.fallback.generate_financial_advice(query, context)

        import urllib.request
        import json

        system_instruction = (
            "You are the empathetic, culturally aware, dialect-sensitive AI Financial Coach for 'upay Pulse' Mobile Financial Services (MFS) in Bangladesh. "
            "The user is an everyday citizen, small merchant, or garment worker. "
            "Always reply in natural, friendly, polite colloquial Bengali (বাংলা). "
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

        # Try candidate models in order of speed and availability
        for model in self.CANDIDATE_MODELS:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    text = result["candidates"][0]["content"]["parts"][0]["text"].strip()

                    # Infer intent category for analytics
                    q_low = query.lower()
                    if any(w in q_low for w in ["ব্যালেন্স", "টাকা আছে", "balance"]):
                        intent = "BALANCE_INQUIRY"
                    elif any(w in q_low for w in ["বিল", "বাকি", "ঘাটতি", "bill"]):
                        intent = "DEFICIT_ALERT"
                    elif any(w in q_low for w in ["গ্রেস", "লোন", "ধার", "grace", "loan"]):
                        intent = "GRACE_ELIGIBILITY"
                    elif any(w in q_low for w in ["এফডিআর", "সঞ্চয়", "fdr", "saving"]):
                        intent = "MICRO_FDR"
                    elif any(w in q_low for w in ["কোথায় খরচ", "খরচ বেশি", "spending"]):
                        intent = "SPENDING_INSIGHT"
                    else:
                        intent = "GENERAL_GUIDE"

                    return text, intent

            except Exception:
                continue

        # Resilient offline fallback if all cloud models fail, timeout, or rate-limit
        return self.fallback.generate_financial_advice(query, context)

def get_ai_provider() -> AIProvider:
    """Factory to retrieve active AI provider based on configuration."""
    if settings.AI_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider(api_key=settings.GEMINI_API_KEY)
    return MockLocalProvider()
