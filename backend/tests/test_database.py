import pytest
from sqlalchemy import text
from backend.app.core.database import SessionLocal
from backend.app.core.security import verify_password, verify_freeze_pin
from backend.app.models import (
    User, UserRole, CustomerProfile, AgentProfile,
    Transaction, RiskScore, CashFlowForecast, Notification, AuditLog
)

def test_database_connection():
    db = SessionLocal()
    try:
        val = db.execute(text("SELECT 1")).scalar()
        assert val == 1
    finally:
        db.close()

def test_baseline_users_seeded():
    db = SessionLocal()
    try:
        customer = db.query(User).filter(User.email == "customer@example.com").first()
        assert customer is not None
        assert customer.role == UserRole.CUSTOMER
        assert verify_password("Demo@1234", customer.hashed_password)
        assert verify_freeze_pin("1234", customer.freeze_pin_hash)
        assert customer.customer_profile is not None
        assert float(customer.customer_profile.wallet_balance) == 500.00

        agent = db.query(User).filter(User.email == "agent@example.com").first()
        assert agent is not None
        assert agent.role == UserRole.AGENT
        assert agent.agent_profile is not None
        assert agent.agent_profile.agent_code == "AGT-1001"
        assert float(agent.agent_profile.float_balance) == 120000.00

        admin = db.query(User).filter(User.email == "admin@example.com").first()
        assert admin is not None
        assert admin.role == UserRole.ADMIN
    finally:
        db.close()

def test_transaction_and_risk_score_relationship():
    db = SessionLocal()
    try:
        txn = db.query(Transaction).filter(Transaction.transaction_reference == "TXN-ANOMALY-002").first()
        assert txn is not None
        assert txn.is_flagged_fraud is True
        assert txn.risk_score is not None
        assert float(txn.risk_score.risk_score) == 0.89
        assert txn.risk_score.risk_level.value == "HIGH"
    finally:
        db.close()

def test_cash_flow_forecasts_exist():
    db = SessionLocal()
    try:
        customer = db.query(User).filter(User.email == "customer@example.com").first()
        forecasts = db.query(CashFlowForecast).filter(
            CashFlowForecast.customer_id == customer.customer_profile.id
        ).all()
        assert len(forecasts) >= 14
    finally:
        db.close()
