"""
upay Pulse — Automated Dynamic Nonce Attack Benchmark (Workstream 9)
Executes 4 cryptographic attack vectors to prove anti-counterfeit defense:
- Attack 1: Static screenshot capture
- Attack 2: Expired nonce replay
- Attack 3: Modified / tampered nonce
- Attack 4: Multi-merchant token replay
"""

import time
import pytest
from backend.app.services.badge_service import BadgeService
from backend.app.core.database import SessionLocal

def test_dynamic_nonce_attack_suite():
    db = SessionLocal()
    ref = "TXN-INIT-001"
    now_bucket = int(time.time()) // 60

    try:
        # Generate authentic baseline live nonce
        live_badge = BadgeService.generate_badge(db, ref)
        assert live_badge["status"] == "COMPLETED"
        valid_nonce = live_badge["dynamic_nonce"]

        # -------------------------------------------------------------
        # Attack 1: Static Screenshot Replay
        # Attacker took a photo of completed payment 10 minutes ago
        # -------------------------------------------------------------
        old_bucket = now_bucket - 10
        old_screenshot_nonce = BadgeService._compute_nonce(ref, old_bucket)
        res_attack_1 = BadgeService.verify_badge(db, ref, old_screenshot_nonce)
        assert res_attack_1["is_valid"] is False
        assert res_attack_1["verification_status"] == "EXPIRED_OR_COUNTERFEIT"

        # -------------------------------------------------------------
        # Attack 2: Expired Nonce Token (Presentation after 120 seconds)
        # -------------------------------------------------------------
        expired_bucket = now_bucket - 3
        expired_nonce = BadgeService._compute_nonce(ref, expired_bucket)
        res_attack_2 = BadgeService.verify_badge(db, ref, expired_nonce)
        assert res_attack_2["is_valid"] is False
        assert res_attack_2["verification_status"] == "EXPIRED_OR_COUNTERFEIT"

        # -------------------------------------------------------------
        # Attack 3: Tampered / Fabricated Nonce (Altered character)
        # -------------------------------------------------------------
        # Flip the last character
        tampered_nonce = valid_nonce[:-1] + ("Z" if valid_nonce[-1] != "Z" else "A")
        res_attack_3 = BadgeService.verify_badge(db, ref, tampered_nonce)
        assert res_attack_3["is_valid"] is False
        assert res_attack_3["verification_status"] == "EXPIRED_OR_COUNTERFEIT"

        # -------------------------------------------------------------
        # Attack 4: Token Replay Attack (Reusing consumed single-use nonce)
        # -------------------------------------------------------------
        # Step 4a: First merchant presents and consumes valid nonce
        res_legit = BadgeService.verify_badge(db, ref, valid_nonce, consume=True)
        assert res_legit["is_valid"] is True
        assert res_legit["verification_status"] == "AUTHENTIC_LIVE"

        # Step 4b: Second merchant counter attempts to reuse the same nonce
        res_attack_4 = BadgeService.verify_badge(db, ref, valid_nonce, consume=True)
        assert res_attack_4["is_valid"] is False
        assert res_attack_4["verification_status"] == "REPLAY_ATTACK_BLOCKED"

    finally:
        BadgeService._consumed_nonces.clear()
        db.close()
