"""
upay Pulse - Software Soundbox Service
Generates auditory payment confirmation chimes and Bengali voice notification metadata
for MFS merchant & agent terminals upon successful cash-in / merchant payment.
"""

import io
import wave
import struct
import math
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

    @classmethod
    def generate_chime_wav(cls, amount: float = 500.0) -> bytes:
        """Synthesize pure C5-E5-G5 acoustic triad chime as a 16-bit PCM WAV file."""
        sample_rate = 22050
        duration = 1.2
        total_samples = int(sample_rate * duration)
        freqs = [523.25, 659.25, 783.99]
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            frames = bytearray()
            for i in range(total_samples):
                t = float(i) / sample_rate
                sample_val = 0.0
                for idx, freq in enumerate(freqs):
                    delay = idx * 0.08
                    if t >= delay:
                        sub_t = t - delay
                        sub_env = math.exp(-3.5 * sub_t)
                        sample_val += math.sin(2.0 * math.pi * freq * sub_t) * sub_env
                sample_val = (sample_val / len(freqs)) * 32767.0 * 0.7
                sample_int = int(max(-32767, min(32767, sample_val)))
                frames.extend(struct.pack('<h', sample_int))
            wav.writeframes(frames)
        return buffer.getvalue()
