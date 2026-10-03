"""
upay Pulse - Software Soundbox Service
Generates auditory payment confirmation chimes and Bengali voice notification metadata
for MFS merchant & agent terminals upon successful cash-in / merchant payment.
"""

from typing import Dict, Any, Optional
from backend.app.core.exceptions import AppException
from backend.app.models.transaction import Transaction, TransactionStatus

class SoundboxService:

    @classmethod
    def generate_payment_chime(cls, transaction: Transaction) -> Dict[str, Any]:
        """
        Creates soundbox audio metadata and Bengali vocal script for transaction.
        e.g. 'উপায় পেমেন্ট সফল! ৳৫০০ টাকা জমা হয়েছে।'
        """
        if transaction.status != TransactionStatus.COMPLETED:
            raise AppException(
                message="Soundbox chimes can only be generated for COMPLETED transactions.",
                code="TRANSACTION_NOT_COMPLETED",
                status_code=400
            )

        amount = float(transaction.amount)
        ref = transaction.transaction_reference

        # Bengali number representation helper
        bengali_digits = {'0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪', '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'}
        amount_bn = "".join(bengali_digits.get(c, c) for c in f"{amount:,.2f}".replace(".00", ""))

        vocal_script_bangla = f"উপায় সফল! {amount_bn} টাকা জমা হয়েছে।"
        vocal_script_english = f"upay Success! {amount:,.2f} BDT received."

        return {
            "transaction_reference": ref,
            "amount": amount,
            "amount_bangla": amount_bn,
            "vocal_script_bangla": vocal_script_bangla,
            "vocal_script_english": vocal_script_english,
            "chime_tone_frequency_hz": [523.25, 659.25, 783.99], # C5, E5, G5 major triad chime
            "chime_duration_ms": 1200,
            "audio_url": f"/api/v1/soundbox/chime/{ref}.wav",
            "soundbox_status": "BROADCAST_READY"
        }
