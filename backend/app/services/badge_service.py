"""
upay Pulse - Anti-Screenshot Dynamic Payment Badge Service
Generates rotating cryptographic nonces and real-time visual pulse metadata
to protect merchants and agents from counterfeit / altered screenshot fraud.
"""

import time
import hmac
import hashlib
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.exceptions import AppException
from backend.app.models.transaction import Transaction, TransactionStatus

class BadgeService:

    @classmethod
    def _compute_nonce(cls, reference: str, time_bucket: int) -> str:
        """
        Computes 6-character cryptographic nonce for a reference within a 60-second time window.
        """
        key = settings.SECRET_KEY.encode("utf-8")
        msg = f"{reference}:{time_bucket}".encode("utf-8")
        digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return digest[:6].upper()

    @classmethod
    def generate_badge(cls, db: Session, transaction_reference: str) -> Dict[str, Any]:
        """
        Generates dynamic anti-screenshot badge metadata for a transaction.
        """
        txn = db.query(Transaction).filter(
            Transaction.transaction_reference == transaction_reference
        ).first()

        if not txn:
            raise AppException("Transaction reference not found.", code="TRANSACTION_NOT_FOUND", status_code=404)

        if txn.status != TransactionStatus.COMPLETED:
            raise AppException("Payment badge only available for completed transactions.", code="INVALID_STATUS", status_code=400)

        now = int(time.time())
        time_bucket = now // 60
        seconds_remaining = 60 - (now % 60)
        nonce = cls._compute_nonce(transaction_reference, time_bucket)

        # Dynamic visual pulse colors based on time bucket to thwart screenshots
        pulse_colors = ["#10B981", "#06B6D4", "#6366F1", "#8B5CF6"]
        active_color = pulse_colors[time_bucket % len(pulse_colors)]

        return {
            "transaction_reference": txn.transaction_reference,
            "amount": float(txn.amount),
            "recipient_name": txn.receiver.phone if txn.receiver else "Merchant",
            "category": txn.category,
            "status": "COMPLETED",
            "dynamic_nonce": nonce,
            "pulse_color": active_color,
            "pulse_frequency_hz": 1.25,
            "seconds_remaining_in_window": seconds_remaining,
            "created_at": txn.created_at.isoformat() if txn.created_at else None,
            "security_disclaimer": "Live Cryptographic Anti-Screenshot Nonce. Static image captures are invalid."
        }

    @classmethod
    def verify_badge(cls, db: Session, transaction_reference: str, nonce: str) -> Dict[str, Any]:
        """
        Verifies whether presented dynamic nonce matches the authentic active or recent time window.
        Prevents acceptance of static screenshots or altered images.
        """
        txn = db.query(Transaction).filter(
            Transaction.transaction_reference == transaction_reference
        ).first()

        if not txn:
            return {
                "is_valid": False,
                "verification_status": "NOT_FOUND",
                "message": "Transaction does not exist in Central Ledger."
            }

        if txn.status != TransactionStatus.COMPLETED:
            return {
                "is_valid": False,
                "verification_status": "UNSETTLED",
                "message": f"Transaction status is {txn.status}, not settled."
            }

        now = int(time.time())
        current_bucket = now // 60
        input_nonce = nonce.strip().upper()

        # Check current bucket and previous bucket (60s tolerance for customer presentation)
        valid_nonces = [
            cls._compute_nonce(transaction_reference, current_bucket),
            cls._compute_nonce(transaction_reference, current_bucket - 1)
        ]

        if input_nonce in valid_nonces:
            return {
                "is_valid": True,
                "verification_status": "AUTHENTIC_LIVE",
                "transaction_reference": txn.transaction_reference,
                "amount": float(txn.amount),
                "created_at": txn.created_at.isoformat() if txn.created_at else None,
                "message": "[VERIFIED] Legitimate live transaction. Anti-screenshot cryptographic signature valid."
            }
        else:
            return {
                "is_valid": False,
                "verification_status": "EXPIRED_OR_COUNTERFEIT",
                "transaction_reference": txn.transaction_reference,
                "amount": float(txn.amount),
                "message": "[FRAUD WARNING] Nonce mismatch! Likely a static screenshot, recording, or fabricated payment."
            }
