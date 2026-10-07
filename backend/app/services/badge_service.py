"""
upay Pulse - Anti-Screenshot Dynamic Payment Badge Service
Generates rotating cryptographic nonces and real-time visual pulse metadata
to protect merchants and agents from counterfeit / altered screenshot fraud.
"""

import time
import hmac
import hashlib
from typing import Dict, Any, List, Optional
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

    _consumed_nonces = set()

    @classmethod
    def verify_badge(cls, db: Session, transaction_reference: str, nonce: str, consume: bool = False) -> Dict[str, Any]:
        """
        Verifies whether presented dynamic nonce matches the authentic active or recent time window.
        Prevents acceptance of static screenshots, altered images, and token replay.
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
        nonce_key = f"{transaction_reference}:{input_nonce}"

        # Replay Attack Detection
        if nonce_key in cls._consumed_nonces:
            return {
                "is_valid": False,
                "verification_status": "REPLAY_ATTACK_BLOCKED",
                "transaction_reference": txn.transaction_reference,
                "amount": float(txn.amount),
                "message": "[SECURITY BLOCKED] Token replay attack detected! Nonce has already been validated and consumed."
            }

        # Check current bucket and previous bucket (60s tolerance for customer presentation)
        valid_nonces = [
            cls._compute_nonce(transaction_reference, current_bucket),
            cls._compute_nonce(transaction_reference, current_bucket - 1)
        ]

        if input_nonce in valid_nonces:
            if consume:
                cls._consumed_nonces.add(nonce_key)
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

    @classmethod
    def run_attack_suite(cls, db: Session, transaction_reference: str) -> Dict[str, Any]:
        """
        Executes the four canonical anti-screenshot attack scenarios against the
        real BadgeService verifier. Returns a structured report that the
        /api/v1/security/attack-suite/run endpoint and the pytest suite both
        consume, so the live API and the automated test cannot diverge.

        Returns:
            {
              "transaction_reference": "...",
              "results": [
                {"id": 1, "name": "Static Screenshot",     "blocked": True, "verification_status": "EXPIRED_OR_COUNTERFEIT"},
                {"id": 2, "name": "Expired Token",         "blocked": True, "verification_status": "EXPIRED_OR_COUNTERFEIT"},
                {"id": 3, "name": "Tampered Nonce",        "blocked": True, "verification_status": "EXPIRED_OR_COUNTERFEIT"},
                {"id": 4, "name": "Token Replay",          "blocked": True, "verification_status": "REPLAY_ATTACK_BLOCKED"}
              ],
              "passed": 4,
              "total":  4
            }
        """
        results: List[Dict[str, Any]] = []

        # Generate authentic baseline live nonce for the same reference.
        live = cls.generate_badge(db, transaction_reference)
        valid_nonce = live["dynamic_nonce"]

        now_bucket = int(time.time()) // 60

        # Attack 1: static screenshot — nonce from 10 minutes ago.
        old_screenshot_nonce = cls._compute_nonce(transaction_reference, now_bucket - 10)
        r1 = cls.verify_badge(db, transaction_reference, old_screenshot_nonce)
        results.append({
            "id": 1,
            "name": "Static Screenshot",
            "blocked": r1["is_valid"] is False,
            "verification_status": r1["verification_status"],
        })

        # Attack 2: expired token — nonce from 3 buckets ago.
        expired_nonce = cls._compute_nonce(transaction_reference, now_bucket - 3)
        r2 = cls.verify_badge(db, transaction_reference, expired_nonce)
        results.append({
            "id": 2,
            "name": "Expired Token",
            "blocked": r2["is_valid"] is False,
            "verification_status": r2["verification_status"],
        })

        # Attack 3: tampered nonce — flip the last hex character.
        tampered = valid_nonce[:-1] + ("Z" if valid_nonce[-1] != "Z" else "A")
        r3 = cls.verify_badge(db, transaction_reference, tampered)
        results.append({
            "id": 3,
            "name": "Tampered Nonce",
            "blocked": r3["is_valid"] is False,
            "verification_status": r3["verification_status"],
        })

        # Attack 4: token replay — first verify (consume), then attempt second time.
        first = cls.verify_badge(db, transaction_reference, valid_nonce, consume=True)
        second = cls.verify_badge(db, transaction_reference, valid_nonce, consume=True)
        results.append({
            "id": 4,
            "name": "Token Replay",
            "blocked": second["is_valid"] is False,
            "verification_status": second["verification_status"],
            "first_call_status": first["verification_status"],
        })

        passed = sum(1 for r in results if r["blocked"])
        return {
            "transaction_reference": transaction_reference,
            "results": results,
            "passed": passed,
            "total": len(results),
        }
