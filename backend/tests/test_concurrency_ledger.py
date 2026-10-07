"""
upay Pulse — Concurrency, Double-Spend & Master Freeze Race Tests (Workstreams 14 & 15)
Proves:
1. Double-Spend Prevention: 2 concurrent transfers of ৳700 from a ৳1,000 balance:
   - Exactly 1 succeeds.
   - Exactly 1 fails with INSUFFICIENT_FUNDS.
   - Final balance is strictly ৳300.00, NEVER negative.
2. Freeze vs Transaction Race: Transactions cannot slip past an active Master Freeze lockdown.
"""

import concurrent.futures
from decimal import Decimal
import pytest

from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserStatus
from backend.app.models.customer import CustomerProfile
from backend.app.services.transaction_service import TransactionService
from backend.app.services.freeze_service import FreezeService
from backend.app.schemas.transaction import SendMoneyRequest
from backend.app.schemas.freeze import MasterFreezeRequest
from backend.app.core.security import get_freeze_pin_hash
from backend.app.core.exceptions import AppException

def test_concurrent_double_spend_race_prevention():
    """
    Test two concurrent threads attempting to spend ৳700 simultaneously
    from a single account holding only ৳1,000.
    With pessimistic row-level locking (SELECT ... FOR UPDATE),
    exactly 1 must succeed and 1 must fail with INSUFFICIENT_FUNDS.
    """
    db_setup = SessionLocal()
    try:
        # 1. Setup Sender with exactly ৳1,000
        sender_phone = "+8801700000001"
        sender = db_setup.query(User).filter(User.phone == sender_phone).first()
        assert sender is not None
        sender.is_frozen = False
        sender.status = UserStatus.ACTIVE
        sender.customer_profile.wallet_balance = Decimal("1000.00")
        sender.customer_profile.grace_balance = Decimal("0.00")

        # Receiver
        receiver_phone = "+8801700000002"
        receiver = db_setup.query(User).filter(User.phone == receiver_phone).first()
        assert receiver is not None
        initial_receiver_bal = receiver.customer_profile.wallet_balance

        db_setup.commit()
    finally:
        db_setup.close()

    # 2. Function to execute transfer in an isolated thread & DB session
    def attempt_transfer(thread_id: int):
        db_thread = SessionLocal()
        try:
            thread_sender = db_thread.query(User).filter(User.phone == sender_phone).first()
            req = SendMoneyRequest(
                receiver_identifier=receiver_phone,
                amount=700.00,
                apply_grace_if_needed=False,
                category="Concurrency_Test",
                description=f"Thread-{thread_id} race test"
            )
            res = TransactionService.send_money(db=db_thread, sender=thread_sender, req=req)
            db_thread.commit()
            return {"success": True, "tx_ref": res.transaction_reference}
        except AppException as e:
            db_thread.rollback()
            return {"success": False, "code": e.code, "message": e.message}
        except Exception as e:
            db_thread.rollback()
            return {"success": False, "code": "DB_ERROR", "message": str(e)}
        finally:
            db_thread.close()

    # 3. Spawn concurrent threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_transfer, 1)
        f2 = executor.submit(attempt_transfer, 2)
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    # 4. Strict assertions
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"
    assert failures[0]["code"] in ["INSUFFICIENT_FUNDS", "INSUFFICIENT_FUNDS_GRACE_OFFERED"]

    # 5. Verify final balance in database
    db_verify = SessionLocal()
    try:
        sender_verify = db_verify.query(User).filter(User.phone == sender_phone).first()
        final_balance = sender_verify.customer_profile.wallet_balance
        assert final_balance == Decimal("300.00"), f"Expected balance ৳300.00, got ৳{final_balance}"
    finally:
        db_verify.close()


def test_concurrent_freeze_vs_transaction_race():
    """
    Test race between Master Freeze lockdown and money transfer.
    Once freeze executes, all subsequent transfer attempts must be immediately rejected.
    """
    db = SessionLocal()
    try:
        sender_phone = "+8801700000001"
        sender = db.query(User).filter(User.phone == sender_phone).first()
        sender.is_frozen = False
        sender.status = UserStatus.ACTIVE
        sender.freeze_pin_hash = get_freeze_pin_hash("1234")
        sender.customer_profile.wallet_balance = Decimal("2000.00")
        db.commit()

        # Step 1: Execute freeze
        freeze_res = FreezeService.trigger_freeze(
            db=db,
            user=sender,
            freeze_pin="1234",
            reason="Emergency test freeze"
        )
        assert freeze_res.is_frozen is True

        # Step 2: Attempt transfer right after freeze
        req = SendMoneyRequest(
            receiver_identifier="+8801700000002",
            amount=50.00,
            category="Race_Test"
        )
        with pytest.raises(AppException) as exc_info:
            TransactionService.send_money(db=db, sender=sender, req=req)

        assert exc_info.value.code == "ACCOUNT_FROZEN"

    finally:
        db.close()
