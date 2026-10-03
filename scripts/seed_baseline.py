import sys
import os
from datetime import date, datetime, timedelta, timezone

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash, get_freeze_pin_hash
from backend.app.models import (
    User, UserRole, UserStatus,
    CustomerProfile, AgentProfile,
    Transaction, TransactionType, TransactionStatus,
    RiskScore, RiskLevel, RiskDecision,
    CashFlowForecast, Notification, NotificationType,
    AuditLog
)

def seed_baseline_data():
    db = SessionLocal()
    try:
        print("Seeding baseline demo accounts for upay Pulse...")
        
        # 1. Clean existing test data safely
        db.query(AuditLog).delete()
        db.query(Notification).delete()
        db.query(CashFlowForecast).delete()
        db.query(RiskScore).delete()
        db.query(Transaction).delete()
        db.query(CustomerProfile).delete()
        db.query(AgentProfile).delete()
        db.query(User).delete()
        db.commit()

        # 2. Baseline Customer: customer@example.com (Balance: 500 BDT)
        user_customer = User(
            phone="+8801700000001",
            email="customer@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            freeze_pin_hash=get_freeze_pin_hash("1234"),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE
        )
        db.add(user_customer)
        db.flush()

        profile_customer = CustomerProfile(
            user_id=user_customer.id,
            full_name="Arif Hossain",
            profession="Textile Merchandiser",
            location="Gazipur, Dhaka",
            wallet_balance=500.00,
            grace_balance=0.00,
            reliability_score=0.92,
            avg_monthly_inflow=22000.00,
            avg_monthly_outflow=20500.00,
            spending_pattern="Utility Bills & Family Remittance"
        )
        db.add(profile_customer)

        # 3. Victim Customer: victim@example.com (Balance: 25,000 BDT)
        user_victim = User(
            phone="+8801700000002",
            email="victim@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            freeze_pin_hash=get_freeze_pin_hash("4321"),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE
        )
        db.add(user_victim)
        db.flush()

        profile_victim = CustomerProfile(
            user_id=user_victim.id,
            full_name="Nasir Uddin",
            profession="Small Business Owner",
            location="Dhanmondi, Dhaka",
            wallet_balance=25000.00,
            grace_balance=0.00,
            reliability_score=0.88,
            avg_monthly_inflow=60000.00,
            avg_monthly_outflow=45000.00,
            spending_pattern="Merchant Supplies"
        )
        db.add(profile_victim)

        # 4. Merchant/Agent: agent@example.com (Savar Industrial Point)
        user_agent = User(
            phone="+8801800000001",
            email="agent@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            role=UserRole.AGENT,
            status=UserStatus.ACTIVE
        )
        db.add(user_agent)
        db.flush()

        profile_agent = AgentProfile(
            user_id=user_agent.id,
            agent_code="AGT-1001",
            store_name="Savar Digital Pay Point",
            location_cluster="Savar Garment Zone",
            cash_balance=45000.00,
            float_balance=120000.00,
            daily_cash_out_volume=85000.00,
            is_factory_zone=True
        )
        db.add(profile_agent)

        # 5. Risk Analyst / Admin: admin@example.com
        user_admin = User(
            phone="+8801900000001",
            email="admin@example.com",
            hashed_password=get_password_hash("Admin@1234"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        db.add(user_admin)
        db.flush()

        # 6. Seed Baseline Transactions & Risk Scores
        txn1 = Transaction(
            transaction_reference="TXN-INIT-001",
            sender_id=user_victim.id,
            receiver_id=user_customer.id,
            amount=500.00,
            fee=5.00,
            transaction_type=TransactionType.SEND_MONEY,
            status=TransactionStatus.COMPLETED,
            category="Transfer",
            description="Initial seed transfer"
        )
        db.add(txn1)
        db.flush()

        risk1 = RiskScore(
            transaction_id=txn1.id,
            risk_score=0.05,
            risk_level=RiskLevel.LOW,
            decision=RiskDecision.ALLOW,
            reasons='["Standard daytime peer transfer", "Known relationship"]',
            inference_latency_ms=12.4
        )
        db.add(risk1)

        # High risk anomalous transaction (for demo detection)
        txn2 = Transaction(
            transaction_reference="TXN-ANOMALY-002",
            sender_id=user_victim.id,
            receiver_id=user_agent.id,
            amount=24500.00,
            fee=45.00,
            transaction_type=TransactionType.CASH_OUT,
            status=TransactionStatus.PENDING_REVIEW,
            category="Cash-Out",
            description="Late night bulk cash-out",
            is_flagged_fraud=True
        )
        db.add(txn2)
        db.flush()

        risk2 = RiskScore(
            transaction_id=txn2.id,
            risk_score=0.89,
            risk_level=RiskLevel.HIGH,
            decision=RiskDecision.BLOCK_AND_FLAG,
            reasons='["Amount deviates +350% from 30d mean", "High velocity transfer 02:45 AM", "Unusual cash-out agent"]',
            inference_latency_ms=28.7
        )
        db.add(risk2)

        # 7. Seed Cash-Flow Projections for Customer 1 (Next 14 days)
        today = date.today()
        current_sim_balance = 500.0
        for i in range(1, 15):
            target_date = today + timedelta(days=i)
            # Simulated typical spending pattern
            daily_outflow = 60.0 if i % 4 != 0 else 180.0
            daily_inflow = 0.0 if i != 10 else 1500.0  # Salary on day 10
            current_sim_balance = current_sim_balance + daily_inflow - daily_outflow
            
            db.add(CashFlowForecast(
                customer_id=profile_customer.id,
                forecast_date=target_date,
                inflow_forecast=daily_inflow,
                outflow_forecast=daily_outflow,
                projected_balance=max(current_sim_balance, 0.0),
                deficit_warning=current_sim_balance < 100.0
            ))

        # 8. Notifications
        db.add(Notification(
            user_id=user_customer.id,
            title="upay Grace Micro-Overdraft Active",
            message="Your high reliability score qualifies you for up to ৳50.00 emergency micro-overdraft.",
            notification_type=NotificationType.GRACE_OFFER
        ))
        db.add(Notification(
            user_id=user_agent.id,
            title="Garment Zone Salary Day Notice",
            message="Anticipated cash-out surge on Thursday (+280%). Ensure minimum ৳80,000 float.",
            notification_type=NotificationType.SURGE_WARNING
        ))

        # 9. Audit Log
        db.add(AuditLog(
            actor_id=user_admin.id,
            actor_role="ADMIN",
            action="SYSTEM_INIT_BASELINE",
            resource="DATABASE",
            details='{"event": "Baseline test dataset seeded successfully"}'
        ))

        db.commit()
        print("[OK] Baseline accounts and demo entities seeded successfully:")
        print("  - Customer: customer@example.com (PIN: 1234, Balance: 500.00 BDT)")
        print("  - Victim: victim@example.com (PIN: 4321, Balance: 25,000.00 BDT)")
        print("  - Agent: agent@example.com (Code: AGT-1001, Savar Garment Zone)")
        print("  - Admin: admin@example.com (Risk Console & System Oversight)")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed baseline data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_baseline_data()
