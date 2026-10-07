import sys
import os
from datetime import date, timedelta
from decimal import Decimal
import random

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash, get_freeze_pin_hash
from backend.app.models import (
    User, UserRole, UserStatus,
    CustomerProfile, AgentProfile,
    Transaction, TransactionType, TransactionStatus,
    RiskScore, RiskLevel, RiskDecision,
    ScamReport, ScamReportStatus, MuleGraphNode, MuleGraphEdge,
    FreezeAction, FreezeActionType,
    GraceOverdraftRequest, GraceStatus,
    MicroFDRAccount, FDRStatus,
    AgentLiquidityForecast,
    VoiceCoachSession,
    CashFlowForecast,
    Notification, NotificationType,
    AuditLog
)


def _add_transaction(db, *, ref, sender_id, receiver_id, agent_id, amount, fee,
                      txn_type, status, category, description,
                      is_flagged=False):
    """Helper that creates a Transaction in the given session."""
    txn = Transaction(
        transaction_reference=ref,
        sender_id=sender_id,
        receiver_id=receiver_id,
        agent_id=agent_id,
        amount=amount,
        fee=fee,
        transaction_type=txn_type,
        status=status,
        category=category,
        description=description,
        is_flagged_fraud=is_flagged,
    )
    db.add(txn)
    db.flush()
    return txn


def _score_for(db, txn, *, risk_score, level, decision, reasons, latency_ms):
    """Create a RiskScore for a given transaction in the given session."""
    rs = RiskScore(
        transaction_id=txn.id,
        risk_score=risk_score,
        risk_level=level,
        decision=decision,
        reasons=reasons,
        inference_latency_ms=latency_ms,
    )
    db.add(rs)
    return rs


def seed_baseline_data(force: bool = False):
    db = SessionLocal()
    try:
        existing_count = db.query(User).count()
        if existing_count > 0 and not force:
            print(f"[INFO] Database already contains {existing_count} users. Baseline accounts ready.")
            return

        print("Seeding rich demo dataset for upay Pulse...")

        # 1. Wipe in reverse dependency order so re-seeding is idempotent.
        db.query(VoiceCoachSession).delete()
        db.query(FreezeAction).delete()
        db.query(GraceOverdraftRequest).delete()
        db.query(MicroFDRAccount).delete()
        db.query(AgentLiquidityForecast).delete()
        db.query(MuleGraphEdge).delete()
        db.query(MuleGraphNode).delete()
        db.query(ScamReport).delete()
        db.query(AuditLog).delete()
        db.query(Notification).delete()
        db.query(CashFlowForecast).delete()
        db.query(RiskScore).delete()
        db.query(Transaction).delete()
        db.query(CustomerProfile).delete()
        db.query(AgentProfile).delete()
        db.query(User).delete()
        db.commit()

        # =====================================================================
        # PERSONA 1: ARIF HOSSAIN — primary CUSTOMER demo
        # =====================================================================
        user_customer = User(
            phone="+8801700000001",
            email="customer@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            freeze_pin_hash=get_freeze_pin_hash("1234"),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
        )
        db.add(user_customer)
        db.flush()

        profile_customer = CustomerProfile(
            user_id=user_customer.id,
            full_name="Arif Hossain",
            profession="Textile Merchandiser",
            location="Gazipur, Dhaka",
            wallet_balance=2850.00,
            grace_balance=0.00,
            reliability_score=0.92,
            avg_monthly_inflow=22000.00,
            avg_monthly_outflow=20500.00,
            spending_pattern="Utility Bills & Family Remittance",
        )
        db.add(profile_customer)
        db.flush()

        # =====================================================================
        # PERSONA 2: NASIR UDDIN — VICTIM in a mule ring (security demo)
        # =====================================================================
        user_victim = User(
            phone="+8801700000002",
            email="victim@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            freeze_pin_hash=get_freeze_pin_hash("4321"),
            role=UserRole.CUSTOMER,
            status=UserStatus.FROZEN,  # already frozen — Master Freeze demo target
            is_frozen=True,
        )
        db.add(user_victim)
        db.flush()

        profile_victim = CustomerProfile(
            user_id=user_victim.id,
            full_name="Nasir Uddin",
            profession="Small Business Owner",
            location="Dhanmondi, Dhaka",
            wallet_balance=3750.00,
            grace_balance=0.00,
            reliability_score=0.88,
            avg_monthly_inflow=60000.00,
            avg_monthly_outflow=45000.00,
            spending_pattern="Merchant Supplies",
        )
        db.add(profile_victim)
        db.flush()

        # =====================================================================
        # PERSONA 3: SAVAR AGENT — primary AGENT demo
        # =====================================================================
        user_agent = User(
            phone="+8801800000001",
            email="agent@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            role=UserRole.AGENT,
            status=UserStatus.ACTIVE,
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
            is_factory_zone=True,
        )
        db.add(profile_agent)
        db.flush()

        # =====================================================================
        # PERSONA 4: ADMIN
        # =====================================================================
        user_admin = User(
            phone="+8801900000001",
            email="admin@example.com",
            hashed_password=get_password_hash("Admin@1234"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user_admin)
        db.flush()

        # =====================================================================
        # EXTRA: secondary customer (peer in transaction history) and 2nd agent
        # =====================================================================
        user_peer = User(
            phone="+8801700000003",
            email="rahima@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
        )
        db.add(user_peer)
        db.flush()

        profile_peer = CustomerProfile(
            user_id=user_peer.id,
            full_name="Rahima Khatun",
            profession="Garment Worker",
            location="Savar, Dhaka",
            wallet_balance=4250.00,
            grace_balance=200.00,
            reliability_score=0.78,
            avg_monthly_inflow=14500.00,
            avg_monthly_outflow=14200.00,
            spending_pattern="Family Essentials",
        )
        db.add(profile_peer)
        db.flush()

        user_agent_2 = User(
            phone="+8801800000002",
            email="agent2@example.com",
            hashed_password=get_password_hash("Demo@1234"),
            role=UserRole.AGENT,
            status=UserStatus.ACTIVE,
        )
        db.add(user_agent_2)
        db.flush()

        profile_agent_2 = AgentProfile(
            user_id=user_agent_2.id,
            agent_code="AGT-1042",
            store_name="Dhanmondi Mobile Money",
            location_cluster="Dhanmondi Residential",
            cash_balance=62000.00,
            float_balance=90000.00,
            daily_cash_out_volume=52000.00,
            is_factory_zone=False,
        )
        db.add(profile_agent_2)
        db.flush()

        # =====================================================================
        # CUSTOMER (ARIF) — TRANSACTION HISTORY
        # 12 transactions across categories, mix of completed and pending
        # =====================================================================
        arif_txns = [
            ("TXN-INIT-001", profile_customer, profile_peer, profile_agent, 500.00, 5.00,
             TransactionType.SEND_MONEY, TransactionStatus.COMPLETED, "Transfer",
             "Initial verified transfer for soundbox and badge demo", False),
            ("TXN-ARIF-001", None, profile_peer, profile_agent, 1500.00, 5.00,
             TransactionType.CASH_OUT, TransactionStatus.COMPLETED, "Cash-Out",
             "Family withdrawal — weekend groceries", False),
            ("TXN-ARIF-002", profile_peer, None, None, 800.00, 3.50,
             TransactionType.SEND_MONEY, TransactionStatus.COMPLETED, "Transfer",
             "Repayment to Rahima", False),
            ("TXN-ARIF-003", None, profile_agent, None, 350.00, 2.50,
             TransactionType.BILL_PAY, TransactionStatus.COMPLETED, "Utility Bill",
             "DESCO electricity bill — September", False),
            ("TXN-ARIF-004", None, profile_agent, None, 200.00, 2.00,
             TransactionType.RECHARGE, TransactionStatus.COMPLETED, "Mobile Recharge",
             "GP Flexiplan recharge", False),
            ("TXN-ARIF-005", None, profile_agent, None, 75.00, 1.50,
             TransactionType.MERCHANT_PAY, TransactionStatus.COMPLETED, "Merchant",
             "Tea stall & breakfast", False),
            ("TXN-ARIF-006", None, None, None, 5000.00, 0.00,
             TransactionType.CASH_IN, TransactionStatus.COMPLETED, "Salary",
             "Monthly salary credit from employer", False),
            ("TXN-ARIF-007", profile_victim, None, None, 500.00, 5.00,
             TransactionType.SEND_MONEY, TransactionStatus.COMPLETED, "Transfer",
             "Initial seed transfer", False),
            ("TXN-ARIF-008", None, profile_agent, None, 1200.00, 4.00,
             TransactionType.BILL_PAY, TransactionStatus.COMPLETED, "Utility Bill",
             "Titas gas bill — August", False),
            ("TXN-ARIF-009", None, profile_agent, None, 240.00, 2.00,
             TransactionType.MERCHANT_PAY, TransactionStatus.COMPLETED, "Merchant",
             "Pharmacy & medicine", False),
            ("TXN-ARIF-010", profile_customer, None, None, 350.00, 2.50,
             TransactionType.SEND_MONEY, TransactionStatus.PENDING_REVIEW, "Transfer",
             "Pending — verify recipient", False),
            ("TXN-ARIF-011", None, profile_agent, None, 99.00, 1.50,
             TransactionType.RECHARGE, TransactionStatus.COMPLETED, "Internet",
             "BTCL home internet bill", False),
            ("TXN-ARIF-012", None, profile_agent, None, 1800.00, 5.00,
             TransactionType.CASH_OUT, TransactionStatus.COMPLETED, "Cash-Out",
             "House rent share — November", False),
        ]
        for ref, sender, receiver, agent, amount, fee, ttype, status, cat, desc, flagged in arif_txns:
            _add_transaction(
                db,
                ref=ref,
                sender_id=sender.user_id if sender else None,
                receiver_id=receiver.user_id if receiver else None,
                agent_id=agent.user_id if agent else None,
                amount=amount, fee=fee,
                txn_type=ttype, status=status,
                category=cat, description=desc,
                is_flagged=flagged,
            )

        # =====================================================================
        # RISK SCORES — mix of LOW/MEDIUM/HIGH for Risk Console demo
        # =====================================================================
        all_txns = db.query(Transaction).all()
        for t in all_txns:
            if t.is_flagged_fraud:
                continue  # will be set below with hand-crafted HIGH scores
            # Default LOW scores for routine transactions
            _score_for(
                db,
                t,
                risk_score=round(random.uniform(0.02, 0.18), 3),
                level=RiskLevel.LOW,
                decision=RiskDecision.ALLOW,
                reasons='["Normal transaction pattern", "Within user baseline"]',
                latency_ms=round(random.uniform(6.0, 18.0), 1),
            )

        # =====================================================================
        # SECURITY AI — FRAUD RING
        # Victim (Nasir) gets social-engineered into sending to 3 mule accounts,
        # which fan-out to 2 cash-out agents (Savar + Dhanmondi).
        # =====================================================================
        CLUSTER_ID = "CLUSTER-DEMO-001"

        # Mule account numbers (synthetic 10-digit numbers; real format prefix)
        mules = [
            ("MULE-7001", "SUSPECT_MULE", 0.78),
            ("MULE-7002", "SUSPECT_MULE", 0.81),
            ("MULE-7003", "SUSPECT_MULE", 0.74),
        ]
        mule_nodes = []
        for acc, ntype, score in mules:
            n = MuleGraphNode(
                account_number=acc,
                cluster_id=CLUSTER_ID,
                node_type=ntype,
                risk_score=score,
                in_degree=1,
                out_degree=2,
                is_frozen=False,
            )
            db.add(n)
            db.flush()
            mule_nodes.append(n)

        # Victim node
        victim_node = MuleGraphNode(
            account_number=profile_victim.user.phone,
            cluster_id=CLUSTER_ID,
            node_type="VICTIM",
            risk_score=0.95,
            in_degree=0,
            out_degree=3,
            is_frozen=True,
        )
        db.add(victim_node)
        db.flush()

        # Cash-out agents as nodes
        agent_node_1 = MuleGraphNode(
            account_number=profile_agent.user.phone,
            cluster_id=CLUSTER_ID,
            node_type="CASH_OUT_AGENT",
            risk_score=0.82,
            in_degree=2,
            out_degree=0,
            is_frozen=False,
        )
        db.add(agent_node_1)
        db.flush()

        agent_node_2 = MuleGraphNode(
            account_number=profile_agent_2.user.phone,
            cluster_id=CLUSTER_ID,
            node_type="CASH_OUT_AGENT",
            risk_score=0.69,
            in_degree=1,
            out_degree=0,
            is_frozen=False,
        )
        db.add(agent_node_2)
        db.flush()

        # Edges: victim -> each mule (fan-out from victim)
        for m in mule_nodes:
            db.add(MuleGraphEdge(
                source_account=victim_node.account_number,
                target_account=m.account_number,
                cluster_id=CLUSTER_ID,
                total_amount=round(random.uniform(7000, 9500), 2),
                transaction_count=random.randint(2, 4),
                is_fan_out=True,
            ))
        # Mules -> cash-out agents (fan-in)
        for m in mule_nodes[:2]:
            db.add(MuleGraphEdge(
                source_account=m.account_number,
                target_account=agent_node_1.account_number,
                cluster_id=CLUSTER_ID,
                total_amount=round(random.uniform(6000, 9000), 2),
                transaction_count=random.randint(2, 3),
                is_fan_out=False,
            ))
        db.add(MuleGraphEdge(
            source_account=mule_nodes[2].account_number,
            target_account=agent_node_2.account_number,
            cluster_id=CLUSTER_ID,
            total_amount=round(random.uniform(5000, 7000), 2),
            transaction_count=2,
            is_fan_out=False,
        ))

        # High-risk transactions tied to the mule ring (Nasir -> MULE-7001 etc.)
        high_risk_txns = []
        for i, m in enumerate(mule_nodes):
            t = Transaction(
                transaction_reference=f"TXN-FRAUD-{i+1:03d}",
                sender_id=profile_victim.user.id,
                receiver_id=None,  # mule has no user record
                amount=round(random.uniform(7500, 9500), 2),
                fee=round(random.uniform(15, 45), 2),
                transaction_type=TransactionType.SEND_MONEY,
                status=TransactionStatus.BLOCKED,
                category="Transfer",
                description=f"Suspicious transfer to mule account {m.account_number}",
                is_flagged_fraud=True,
            )
            db.add(t)
            db.flush()
            high_risk_txns.append(t)

        # Single late-night bulk cash-out — headline detection event
        big_cashout = Transaction(
            transaction_reference="TXN-ANOMALY-002",
            sender_id=profile_victim.user.id,
            receiver_id=None,
            agent_id=profile_agent.user.id,
            amount=24500.00,
            fee=45.00,
            transaction_type=TransactionType.CASH_OUT,
            status=TransactionStatus.PENDING_REVIEW,
            category="Cash-Out",
            description="Late night bulk cash-out — auto-flagged",
            is_flagged_fraud=True,
        )
        db.add(big_cashout)
        db.flush()
        high_risk_txns.append(big_cashout)

        # Risk scores for fraud transactions
        for i, t in enumerate(high_risk_txns):
            reasons = '["Amount deviates +350% from 30d mean", "High velocity transfer 02:45 AM", "Unusual cash-out agent"]'
            score_val = 0.89 if t.transaction_reference == "TXN-ANOMALY-002" else round(random.uniform(0.82, 0.94), 3)
            _score_for(
                db,
                t,
                risk_score=score_val,
                level=RiskLevel.HIGH,
                decision=RiskDecision.BLOCK_AND_FLAG,
                reasons=reasons,
                latency_ms=round(random.uniform(20.0, 38.0), 1),
            )

        # =====================================================================
        # SCAM REPORTS — multiple statuses for Risk Console triage view
        # =====================================================================
        scam_reasons = [
            ("Suspicious caller impersonating bKash agent", ScamReportStatus.SUBMITTED),
            ("Received SMS about prize lottery from unknown number", ScamReportStatus.ANALYZING),
            ("Friend request on Facebook asking for OTP", ScamReportStatus.CONFIRMED_FRAUD),
        ]
        for reason, status in scam_reasons:
            db.add(ScamReport(
                reporter_id=profile_customer.user.id,
                reported_account="+8801" + str(random.randint(700000000, 999999999)),
                transaction_id=None,
                reason=reason,
                status=status,
                cluster_id=None,
                investigation_notes=(
                    "Pattern matches known social engineering playbook — "
                    "verify with reporter before any refund." if status == ScamReportStatus.ANALYZING
                    else "Cross-referenced with reported scam cluster; "
                         "advised reporter to change all MFS PINs."
                    if status == ScamReportStatus.CONFIRMED_FRAUD
                    else None
                ),
            ))

        # =====================================================================
        # FREEZE ACTION HISTORY on the victim (sub-300ms response_time_ms)
        # =====================================================================
        db.add(FreezeAction(
            user_id=user_victim.id,
            action_type=FreezeActionType.MASTER_FREEZE_TRIGGERED,
            sessions_revoked=2,
            pending_cancelled=4,
            response_time_ms=287.00,
            ip_address="103.95.84.12",
            reason="Anomalous transfer velocity + multiple flagged high-risk transfers",
        ))

        # =====================================================================
        # CASH-FLOW FORECASTS — 30 days for Arif with one visible deficit window
        # =====================================================================
        today = date.today()
        running_balance = float(profile_customer.wallet_balance)
        for i in range(1, 31):
            target_date = today + timedelta(days=i)
            # Simulated typical spending pattern with one deficit week
            if i % 7 == 0:
                # weekly outflow spike (rent)
                daily_outflow = round(random.uniform(1800, 2200), 2)
            elif i % 4 == 0:
                # mid-week utility bill
                daily_outflow = round(random.uniform(180, 280), 2)
            else:
                daily_outflow = round(random.uniform(40, 90), 2)
            # Salary on the 15th and 30th
            daily_inflow = 1500.00 if i in (15, 30) else 0.00
            running_balance = running_balance + daily_inflow - daily_outflow
            db.add(CashFlowForecast(
                customer_id=profile_customer.id,
                forecast_date=target_date,
                inflow_forecast=daily_inflow,
                outflow_forecast=daily_outflow,
                projected_balance=round(max(running_balance, 0.0), 2),
                deficit_warning=running_balance < 200.0,
            ))

        # =====================================================================
        # MICRO-FDR ACCOUNTS — one active, one matured
        # =====================================================================
        db.add(MicroFDRAccount(
            customer_id=profile_customer.id,
            principal_amount=5000.00,
            term_days=30,
            interest_rate_pct=7.50,
            start_date=today - timedelta(days=10),
            maturity_date=today + timedelta(days=20),
            status=FDRStatus.ACTIVE,
        ))
        db.add(MicroFDRAccount(
            customer_id=profile_customer.id,
            principal_amount=2000.00,
            term_days=7,
            interest_rate_pct=6.50,
            start_date=today - timedelta(days=40),
            maturity_date=today - timedelta(days=33),
            status=FDRStatus.MATURED,
        ))

        # =====================================================================
        # GRACE OVERDRAFT HISTORY — one repaid, one active
        # =====================================================================
        db.add(GraceOverdraftRequest(
            customer_id=profile_customer.id,
            transaction_id=None,
            requested_amount=50.00,
            repaid_amount=50.00,
            status=GraceStatus.REPAID,
        ))
        db.add(GraceOverdraftRequest(
            customer_id=profile_peer.id,
            transaction_id=None,
            requested_amount=200.00,
            repaid_amount=0.00,
            status=GraceStatus.APPROVED,
        ))

        # =====================================================================
        # AGENT LIQUIDITY FORECAST — 7 days for Savar agent
        # Includes a Thursday salary-day surge warning
        # =====================================================================
        for i in range(1, 8):
            target_date = today + timedelta(days=i)
            dow = target_date.weekday()  # Monday=0, Thursday=4
            is_thursday = dow == 4
            predicted = round(random.uniform(95000, 115000), 2) if is_thursday else round(random.uniform(45000, 70000), 2)
            recommended = round(predicted * 0.85, 2)
            db.add(AgentLiquidityForecast(
                agent_id=profile_agent.id,
                target_date=target_date,
                hour_of_day=14 if is_thursday else 11,
                predicted_cash_out=predicted,
                recommended_float=recommended,
                surge_flag=is_thursday,
                surge_reason=(
                    "Garment salary day — factory cluster expected +280% cash-out volume"
                    if is_thursday else None
                ),
            ))

        # Dhanmondi agent — calmer forecast (no factory zone)
        for i in range(1, 8):
            target_date = today + timedelta(days=i)
            predicted = round(random.uniform(38000, 60000), 2)
            db.add(AgentLiquidityForecast(
                agent_id=profile_agent_2.id,
                target_date=target_date,
                hour_of_day=12,
                predicted_cash_out=predicted,
                recommended_float=round(predicted * 0.9, 2),
                surge_flag=False,
                surge_reason=None,
            ))

        # =====================================================================
        # NOTIFICATIONS — multiple types per persona
        # =====================================================================
        db.add(Notification(
            user_id=user_customer.id,
            title="upay Grace Micro-Overdraft Active",
            message="Your 0.92 reliability score qualifies you for up to ৳3,500 emergency micro-overdraft.",
            notification_type=NotificationType.GRACE_OFFER,
        ))
        db.add(Notification(
            user_id=user_customer.id,
            title="Cash-Flow Forecast: Deficit Risk on Nov 12",
            message="Your projected balance may dip below ৳200 around Nov 12. Consider a Micro-FDR to smooth it.",
            notification_type=NotificationType.FDR_RECOMMENDATION,
        ))
        db.add(Notification(
            user_id=user_customer.id,
            title="Transaction Approved",
            message="৳1,800 cash-out to Savar Digital Pay Point completed.",
            notification_type=NotificationType.TRANSACTION_UPDATE,
        ))
        db.add(Notification(
            user_id=user_agent.id,
            title="Garment Zone Salary Day Notice",
            message="Anticipated cash-out surge on Thursday (+280%). Ensure minimum ৳80,000 float.",
            notification_type=NotificationType.SURGE_WARNING,
        ))
        db.add(Notification(
            user_id=user_agent.id,
            title="Liquidity Rebalance Recommended",
            message="Your 7-day forecast shows a ৳35,000 funding gap on Day 4.",
            notification_type=NotificationType.SURGE_WARNING,
        ))
        db.add(Notification(
            user_id=user_victim.id,
            title="Master Freeze Engaged",
            message="Your account has been frozen. Sessions revoked: 2. Pending transactions cancelled: 4.",
            notification_type=NotificationType.SECURITY_ALERT,
        ))

        # =====================================================================
        # VOICE COACH HISTORY — pre-populate a couple of past sessions
        # =====================================================================
        db.add(VoiceCoachSession(
            id="vc-seed-001",
            customer_id=user_customer.id,
            query_text="আমার ব্যালেন্স কত?",
            response_bangla="আপনার ওয়ালেটে ৳2,850 টাকা রয়েছে।",
            audio_url="/api/v1/customer-ai/voice-coach/audio/vc-seed-001",
            intent=None,
            latency_ms=Decimal("1840.00"),
        ))

        # =====================================================================
        # AUDIT LOG — multiple entries for Security Console
        # =====================================================================
        db.add(AuditLog(
            actor_id=user_admin.id,
            actor_role="ADMIN",
            action="SYSTEM_INIT_BASELINE",
            resource="DATABASE",
            details='{"event": "Rich baseline dataset seeded", "version": "1.1"}',
        ))
        db.add(AuditLog(
            actor_id=user_admin.id,
            actor_role="ADMIN",
            action="MASTER_FREEZE_EXECUTED",
            resource=f"user:{user_victim.id}",
            details='{"reason": "Anomalous velocity + flagged transfers", "latency_ms": 287}',
        ))
        db.add(AuditLog(
            actor_id=user_admin.id,
            actor_role="ADMIN",
            action="FRAUD_CLUSTER_IDENTIFIED",
            resource=f"cluster:{CLUSTER_ID}",
            details='{"mules": 3, "agents": 2, "victim": "Nasir Uddin"}',
        ))

        db.commit()
        print("[OK] Rich demo dataset seeded:")
        print("  [CustomerAI] Arif Hossain — customer@example.com / Demo@1234 / PIN 1234")
        print("               12 transactions, 30-day forecast, 2 FDRs, 1 repaid grace")
        print("  [CustomerAI] Rahima Khatun — rahima@example.com / Demo@1234 (peer in txns)")
        print("  [SecurityAI] Nasir Uddin — victim@example.com / Demo@1234 / PIN 4321 (frozen)")
        print("               Mule ring CLUSTER-DEMO-001 with 3 mules + 2 cash-out agents")
        print("               4 blocked fraud transactions, 3 scam reports, 1 freeze action")
        print("  [AgentAI]    Savar Digital Pay Point — agent@example.com / Demo@1234")
        print("               7-day liquidity forecast incl. Thursday surge warning")
        print("  [AgentAI]    Dhanmondi Mobile Money — agent2@example.com / Demo@1234")
        print("  [Admin]      Risk Console — admin@example.com / Admin@1234")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed baseline data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    force_seed = "--force" in sys.argv
    seed_baseline_data(force=force_seed)