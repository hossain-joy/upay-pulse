import os
import sys
import argparse
import random
import csv
import json
import secrets
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal

# Add root directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, engine
from backend.app.core.security import get_password_hash, get_freeze_pin_hash
from backend.app.models import (
    Base,
    User, UserRole, UserStatus,
    CustomerProfile, AgentProfile,
    Transaction, TransactionType, TransactionStatus,
    RiskScore, RiskLevel, RiskDecision,
    ScamReport, ScamReportStatus,
    MuleGraphNode, MuleGraphEdge,
    CashFlowForecast, GraceOverdraftRequest, MicroFDRAccount,
    AgentLiquidityForecast, Notification, NotificationType,
    AuditLog
)

# Deterministic Bangladesh Geo-Clusters & Demographics
LOCATIONS = [
    ("Gazipur Garment Belt", True),
    ("Savar Industrial Zone", True),
    ("Narayanganj Export Zone", True),
    ("Chittagong Port Area", False),
    ("Dhanmondi, Dhaka", False),
    ("Gulshan, Dhaka", False),
    ("Uttara, Dhaka", False),
    ("Mirpur, Dhaka", False),
    ("Sylhet Sadar", False),
    ("Rajshahi University Area", False)
]

PROFESSIONS = [
    ("Garment Factory Worker", 14000.0, 13200.0, "Cash-Out & Remittance"),
    ("University Student", 6500.0, 6200.0, "Mobile Recharge & Food"),
    ("Small Business Retailer", 65000.0, 52000.0, "Merchant Pay & Supply"),
    ("Corporate Executive", 85000.0, 68000.0, "Utility Bills & Savings"),
    ("Ride-Share Driver", 28000.0, 24000.0, "Cash-In & Peer Transfer"),
    ("School Teacher", 22000.0, 20000.0, "Family Support & Bills")
]

class SyntheticDataEngine:
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.data_dir = os.path.join(root_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)

    def generate_all(self, num_customers: int = 1000, num_agents: int = 50, num_transactions: int = 50000):
        print(f"\n============================================================")
        print(f"Generating synthetic MFS dataset (Seed: {self.seed})")
        print(f"Target: {num_customers:,} Customers | {num_agents:,} Agents | {num_transactions:,} Transactions")
        print(f"============================================================")

        customers = self._create_synthetic_customers(num_customers)
        agents = self._create_synthetic_agents(num_agents)
        transactions, risk_scores, scam_reports, mule_nodes, mule_edges = self._create_synthetic_transactions(
            customers, agents, num_transactions
        )

        # Save to CSV for model training and analysis
        self._export_to_csv("synthetic_customers.csv", customers)
        self._export_to_csv("synthetic_agents.csv", agents)
        self._export_to_csv("synthetic_transactions.csv", transactions)
        self._export_to_csv("synthetic_scam_reports.csv", scam_reports)

        print("\n[OK] Synthetic generation complete! CSV datasets created in data/")
        return {
            "customers": customers,
            "agents": agents,
            "transactions": transactions,
            "risk_scores": risk_scores,
            "scam_reports": scam_reports,
            "mule_nodes": mule_nodes,
            "mule_edges": mule_edges
        }

    def _create_synthetic_customers(self, count: int):
        print(f"Generating {count:,} customer profiles...")
        customers = []
        base_phone = 1710000000

        for i in range(count):
            phone = f"+880{base_phone + i}"
            email = f"customer_{i+1}@pulse.demo"
            prof_info = random.choice(PROFESSIONS)
            loc_info = random.choice(LOCATIONS)
            
            # Simulated balance calculation based on inflow
            initial_balance = round(random.uniform(50.0, min(5000.0, prof_info[1] * 0.2)), 2)
            reliability = round(random.uniform(0.65, 0.98), 2)

            customers.append({
                "id": str(secrets.token_hex(16)),
                "phone": phone,
                "email": email,
                "full_name": f"User {i+1}",
                "profession": prof_info[0],
                "location": loc_info[0],
                "wallet_balance": initial_balance,
                "grace_balance": 0.00,
                "reliability_score": reliability,
                "avg_monthly_inflow": prof_info[1],
                "avg_monthly_outflow": prof_info[2],
                "spending_pattern": prof_info[3],
                "created_days_ago": random.randint(30, 730)
            })
        return customers

    def _create_synthetic_agents(self, count: int):
        print(f"Generating {count:,} agent terminals...")
        agents = []
        base_phone = 1810000000

        for i in range(count):
            phone = f"+880{base_phone + i}"
            email = f"agent_{i+1}@pulse.demo"
            loc_info = random.choice(LOCATIONS)
            agent_code = f"AGT-{2000 + i}"
            is_factory = loc_info[1]

            # Factory agents have much higher liquidity demands
            cash_bal = round(random.uniform(70000.0, 150000.0) if is_factory else random.uniform(30000.0, 80000.0), 2)
            float_bal = round(random.uniform(120000.0, 250000.0) if is_factory else random.uniform(50000.0, 120000.0), 2)

            agents.append({
                "id": str(secrets.token_hex(16)),
                "phone": phone,
                "email": email,
                "agent_code": agent_code,
                "store_name": f"{loc_info[0].split()[0]} Telecom Point {i+1}",
                "location_cluster": loc_info[0],
                "cash_balance": cash_bal,
                "float_balance": float_bal,
                "daily_cash_out_volume": round(random.uniform(40000.0, 120000.0), 2),
                "is_factory_zone": is_factory
            })
        return agents

    def _create_synthetic_transactions(self, customers, agents, total_count: int):
        print(f"Synthesizing {total_count:,} transactions with behavioral patterns & fraud clusters...")
        transactions = []
        risk_scores = []
        scam_reports = []
        mule_nodes = []
        mule_edges = []

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=90)

        # -------------------------------------------------------------
        # Inject In-Depth Fraud Patterns: 6 Money-Mule Syndicates
        # -------------------------------------------------------------
        mule_clusters_count = max(6, int(total_count * 0.012 / 7))
        print(f"  -> Injecting {mule_clusters_count} money-mule fan-out syndicates...")
        victim_pool = customers[:max(1, len(customers) // 4)]
        mule_pool = customers[max(1, len(customers) // 4):]

        for cluster_idx in range(1, mule_clusters_count + 1):
            cluster_id = f"CLUSTER-MULE-{cluster_idx:03d}"
            mule_agent = random.choice(agents)
            victim = random.choice(victim_pool)
            mule_group = random.sample(mule_pool, min(4, len(mule_pool)))

            # 1. Victim compromised -> transfers ৳45,000 to primary mule
            primary_mule = mule_group[0]
            mule_nodes.append({
                "id": str(secrets.token_hex(16)),
                "account_number": primary_mule["phone"],
                "cluster_id": cluster_id,
                "node_type": "PRIMARY_MULE",
                "risk_score": 0.94,
                "in_degree": 1,
                "out_degree": 3,
                "is_frozen": False
            })

            # Inbound transaction to primary mule
            txn_id = str(secrets.token_hex(16))
            ref = f"TXN-ML-{cluster_idx}01"
            tx_time = start_date + timedelta(days=random.randint(1, 88), hours=random.choice([1, 2, 3, 4]), minutes=random.randint(0, 50))
            transactions.append({
                "id": txn_id,
                "transaction_reference": ref,
                "sender_id": victim["id"],
                "receiver_id": primary_mule["id"],
                "agent_id": None,
                "amount": 45000.00,
                "fee": 15.00,
                "transaction_type": "SEND_MONEY",
                "status": "COMPLETED",
                "category": "PeerTransfer",
                "description": "Suspicious account takeover burst",
                "is_flagged_fraud": True,
                "created_at": tx_time.isoformat(),
                "hour_of_day": 2,
                "is_night_time": 1,
                "amount_zscore": 4.2,
                "velocity_10m": 1
            })
            risk_scores.append({
                "id": str(secrets.token_hex(16)),
                "transaction_id": txn_id,
                "risk_score": 0.92,
                "risk_level": "HIGH",
                "decision": "BLOCK_AND_FLAG",
                "reasons": json.dumps(["Amount deviates +400% from user mean", "Unusual recipient cluster", "Night time transfer"]),
                "inference_latency_ms": 24.5
            })

            # Scam report filed by victim
            scam_reports.append({
                "id": str(secrets.token_hex(16)),
                "reporter_id": victim["id"],
                "reported_account": primary_mule["phone"],
                "transaction_id": txn_id,
                "reason": "Unauthorized account takeover transfer",
                "status": "CONFIRMED_FRAUD",
                "cluster_id": cluster_id
            })

            # 2. Rapid fan-out from Primary Mule to 3 Secondary Mules within 12 minutes
            for sec_idx, sec_mule in enumerate(mule_group[1:4]):
                fan_txn_id = str(secrets.token_hex(16))
                fan_ref = f"TXN-ML-{cluster_idx}0{sec_idx+2}"
                fan_time = tx_time + timedelta(minutes=(sec_idx + 1) * 3)
                fan_amount = 14500.00

                transactions.append({
                    "id": fan_txn_id,
                    "transaction_reference": fan_ref,
                    "sender_id": primary_mule["id"],
                    "receiver_id": sec_mule["id"],
                    "agent_id": None,
                    "amount": fan_amount,
                    "fee": 10.00,
                    "transaction_type": "SEND_MONEY",
                    "status": "COMPLETED",
                    "category": "Fan-Out",
                    "description": "Rapid syndicate fan-out split",
                    "is_flagged_fraud": True,
                    "created_at": fan_time.isoformat(),
                    "hour_of_day": 2,
                    "is_night_time": 1,
                    "amount_zscore": 3.8,
                    "velocity_10m": 4
                })
                risk_scores.append({
                    "id": str(secrets.token_hex(16)),
                    "transaction_id": fan_txn_id,
                    "risk_score": 0.88,
                    "risk_level": "HIGH",
                    "decision": "BLOCK_AND_FLAG",
                    "reasons": json.dumps(["Rapid fan-out distribution", "Short holding time (< 15 mins)"]),
                    "inference_latency_ms": 19.8
                })

                mule_edges.append({
                    "id": str(secrets.token_hex(16)),
                    "source_account": primary_mule["phone"],
                    "target_account": sec_mule["phone"],
                    "cluster_id": cluster_id,
                    "total_amount": fan_amount,
                    "transaction_count": 1,
                    "is_fan_out": True
                })

                # 3. Secondary mules converge and cash-out at single agent
                cashout_id = str(secrets.token_hex(16))
                cashout_time = fan_time + timedelta(minutes=15)
                transactions.append({
                    "id": cashout_id,
                    "transaction_reference": f"TXN-ML-{cluster_idx}C{sec_idx+1}",
                    "sender_id": sec_mule["id"],
                    "receiver_id": mule_agent["id"],
                    "agent_id": mule_agent["id"],
                    "amount": fan_amount - 50.0,
                    "fee": 25.00,
                    "transaction_type": "CASH_OUT",
                    "status": "COMPLETED",
                    "category": "Cash-Out",
                    "description": "Convergence liquidation cash-out",
                    "is_flagged_fraud": True,
                    "created_at": cashout_time.isoformat(),
                    "hour_of_day": 3,
                    "is_night_time": 1,
                    "amount_zscore": 3.1,
                    "velocity_10m": 2
                })
                risk_scores.append({
                    "id": str(secrets.token_hex(16)),
                    "transaction_id": cashout_id,
                    "risk_score": 0.91,
                    "risk_level": "HIGH",
                    "decision": "BLOCK_AND_FLAG",
                    "reasons": json.dumps(["High-risk cash-out convergence", "Night liquidation"]),
                    "inference_latency_ms": 22.0
                })

                mule_edges.append({
                    "id": str(secrets.token_hex(16)),
                    "source_account": sec_mule["phone"],
                    "target_account": mule_agent["agent_code"],
                    "cluster_id": cluster_id,
                    "total_amount": fan_amount - 50.0,
                    "transaction_count": 1,
                    "is_fan_out": False
                })

        # -------------------------------------------------------------
        # Generate Normal & Temporal Patterns (Remaining Count)
        # -------------------------------------------------------------
        remaining_txns = total_count - len(transactions)
        print(f"  -> Generating {remaining_txns:,} standard & temporal transactions...")

        tx_types = ["SEND_MONEY", "MERCHANT_PAY", "BILL_PAY", "RECHARGE", "CASH_IN", "CASH_OUT"]
        type_weights = [0.35, 0.20, 0.15, 0.15, 0.08, 0.07]

        for i in range(remaining_txns):
            # Pick random timestamp within last 90 days with salary/Eid weighting
            rand_day = random.randint(0, 89)
            tx_dt = start_date + timedelta(days=rand_day, seconds=random.randint(0, 86399))
            
            day_of_month = tx_dt.day
            hour = tx_dt.hour
            is_night = 1 if (1 <= hour <= 5) else 0

            # Salary day surge (1st to 7th of month)
            is_salary_surge = 1 <= day_of_month <= 7
            
            # Select transaction type
            if is_salary_surge and random.random() < 0.40:
                tx_type = random.choice(["CASH_OUT", "SEND_MONEY"])
                amount = round(random.uniform(5000.0, 18000.0), 2)
            elif is_night and random.random() < 0.70:
                # Night-time micro charges or occasional anomaly
                tx_type = "RECHARGE"
                amount = round(random.uniform(20.0, 200.0), 2)
            else:
                tx_type = random.choices(tx_types, weights=type_weights)[0]
                if tx_type == "RECHARGE":
                    amount = round(random.uniform(20.0, 500.0), 2)
                elif tx_type == "BILL_PAY":
                    amount = round(random.uniform(300.0, 3500.0), 2)
                elif tx_type == "MERCHANT_PAY":
                    amount = round(random.uniform(100.0, 2500.0), 2)
                elif tx_type == "CASH_OUT":
                    amount = round(random.uniform(500.0, 8000.0), 2)
                elif tx_type == "CASH_IN":
                    amount = round(random.uniform(1000.0, 15000.0), 2)
                else:
                    amount = round(random.uniform(150.0, 5000.0), 2)

            sender = random.choice(customers)
            receiver = random.choice(customers)
            while receiver["id"] == sender["id"]:
                receiver = random.choice(customers)

            agent = random.choice(agents) if tx_type in ["CASH_IN", "CASH_OUT"] else None

            # Calculate synthetic risk attributes
            amount_zscore = round((amount - 2500.0) / 1800.0, 2)
            velocity_10m = 1 if not is_night else random.choice([1, 2])
            
            # Normal transactions have very low fraud flag
            is_fraud = False
            risk_val = round(max(0.01, min(0.38, 0.05 + (0.15 if is_night else 0.0) + (0.10 if amount > 10000 else 0.0))), 3)
            risk_tier = "LOW"
            decision = "ALLOW"
            reasons = ["Regular domestic transaction pattern"]

            # 1.5% chance of spontaneous high-risk / blocked anomaly
            if random.random() < 0.015:
                is_fraud = True
                tx_type = random.choice(["SEND_MONEY", "CASH_OUT"])
                amount = round(random.uniform(25000.0, 48000.0), 2)
                if random.random() < 0.65:
                    hour = random.choice([1, 2, 3, 4])
                    is_night = 1
                    tx_dt = tx_dt.replace(hour=hour)
                risk_val = round(random.uniform(0.78, 0.96), 3)
                risk_tier = "HIGH"
                decision = "BLOCK_AND_FLAG"
                reasons = ["Abnormal amount deviation", "Unusual velocity burst", "Unregistered recipient"]

            txn_id = str(secrets.token_hex(16))
            ref = f"TXN-{secrets.token_hex(4).upper()}"
            
            transactions.append({
                "id": txn_id,
                "transaction_reference": ref,
                "sender_id": sender["id"] if tx_type != "CASH_IN" else (agent["id"] if agent else sender["id"]),
                "receiver_id": receiver["id"] if tx_type != "CASH_OUT" else (agent["id"] if agent else receiver["id"]),
                "agent_id": agent["id"] if agent else None,
                "amount": amount,
                "fee": 5.00 if tx_type == "SEND_MONEY" else (15.00 if tx_type == "CASH_OUT" else 0.00),
                "transaction_type": tx_type,
                "status": "COMPLETED" if not is_fraud else "BLOCKED",
                "category": tx_type.replace("_", " ").title(),
                "description": f"Simulated {tx_type}",
                "is_flagged_fraud": is_fraud,
                "created_at": tx_dt.isoformat(),
                "hour_of_day": hour,
                "is_night_time": is_night,
                "amount_zscore": amount_zscore,
                "velocity_10m": velocity_10m
            })

            risk_scores.append({
                "id": str(secrets.token_hex(16)),
                "transaction_id": txn_id,
                "risk_score": risk_val,
                "risk_level": risk_tier,
                "decision": decision,
                "reasons": json.dumps(reasons),
                "inference_latency_ms": round(random.uniform(8.5, 32.0), 1)
            })

        return transactions, risk_scores, scam_reports, mule_nodes, mule_edges

    def _export_to_csv(self, filename: str, records: list):
        if not records:
            return
        filepath = os.path.join(self.data_dir, filename)
        keys = list(records[0].keys())
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(records)
        print(f"  [CSV] Saved {len(records):,} records to {filepath}")

    def seed_database(self, generated_data: dict, batch_size: int = 2000):
        """Insert synthetic datasets into PostgreSQL database in fast, memory-safe streaming batches."""
        db = SessionLocal()
        print(f"\nConnecting to PostgreSQL for batch bulk insertion (batch size: {batch_size})...")
        try:
            # 1. Insert Users & Profiles for Customers
            customers = generated_data["customers"]
            agents = generated_data["agents"]
            transactions = generated_data["transactions"]
            risk_scores = generated_data["risk_scores"]
            scam_reports = generated_data["scam_reports"]
            mule_nodes = generated_data["mule_nodes"]
            mule_edges = generated_data["mule_edges"]

            pwd_hash = get_password_hash("Demo@1234")
            pin_hash = get_freeze_pin_hash("1234")

            print(f"Inserting {len(customers):,} customer users & profiles...")
            for i in range(0, len(customers), batch_size):
                chunk = customers[i:i+batch_size]
                users_chunk = []
                profiles_chunk = []
                for c in chunk:
                    users_chunk.append(User(
                        id=c["id"],
                        phone=c["phone"],
                        email=c["email"],
                        hashed_password=pwd_hash,
                        freeze_pin_hash=pin_hash,
                        role=UserRole.CUSTOMER,
                        status=UserStatus.ACTIVE
                    ))
                    profiles_chunk.append(CustomerProfile(
                        id=str(secrets.token_hex(16)),
                        user_id=c["id"],
                        full_name=c["full_name"],
                        profession=c["profession"],
                        location=c["location"],
                        wallet_balance=Decimal(str(c["wallet_balance"])),
                        grace_balance=Decimal("0.00"),
                        reliability_score=Decimal(str(c["reliability_score"])),
                        avg_monthly_inflow=Decimal(str(c["avg_monthly_inflow"])),
                        avg_monthly_outflow=Decimal(str(c["avg_monthly_outflow"])),
                        spending_pattern=c["spending_pattern"]
                    ))
                db.add_all(users_chunk)
                db.flush()
                db.add_all(profiles_chunk)
                db.commit()

            print(f"Inserting {len(agents):,} agent users & profiles...")
            for i in range(0, len(agents), batch_size):
                chunk = agents[i:i+batch_size]
                users_chunk = []
                profiles_chunk = []
                for a in chunk:
                    users_chunk.append(User(
                        id=a["id"],
                        phone=a["phone"],
                        email=a["email"],
                        hashed_password=pwd_hash,
                        role=UserRole.AGENT,
                        status=UserStatus.ACTIVE
                    ))
                    profiles_chunk.append(AgentProfile(
                        id=str(secrets.token_hex(16)),
                        user_id=a["id"],
                        agent_code=a["agent_code"],
                        store_name=a["store_name"],
                        location_cluster=a["location_cluster"],
                        cash_balance=Decimal(str(a["cash_balance"])),
                        float_balance=Decimal(str(a["float_balance"])),
                        daily_cash_out_volume=Decimal(str(a["daily_cash_out_volume"])),
                        is_factory_zone=a["is_factory_zone"]
                    ))
                db.add_all(users_chunk)
                db.flush()
                db.add_all(profiles_chunk)
                db.commit()

            print(f"Inserting {len(transactions):,} transactions and risk scores in streaming batches...")
            for i in range(0, len(transactions), batch_size):
                tx_chunk = transactions[i:i+batch_size]
                rs_chunk = risk_scores[i:i+batch_size]
                
                db_txs = []
                db_risks = []
                for t, r in zip(tx_chunk, rs_chunk):
                    created_dt = datetime.fromisoformat(t["created_at"])
                    db_txs.append(Transaction(
                        id=t["id"],
                        transaction_reference=t["transaction_reference"],
                        sender_id=t["sender_id"],
                        receiver_id=t["receiver_id"],
                        agent_id=t["agent_id"],
                        amount=Decimal(str(t["amount"])),
                        fee=Decimal(str(t["fee"])),
                        transaction_type=TransactionType(t["transaction_type"]),
                        status=TransactionStatus(t["status"]),
                        category=t["category"],
                        description=t["description"],
                        is_flagged_fraud=t["is_flagged_fraud"],
                        created_at=created_dt
                    ))
                    db_risks.append(RiskScore(
                        id=r["id"],
                        transaction_id=r["transaction_id"],
                        risk_score=Decimal(str(r["risk_score"])),
                        risk_level=RiskLevel(r["risk_level"]),
                        decision=RiskDecision(r["decision"]),
                        reasons=r["reasons"],
                        inference_latency_ms=Decimal(str(r["inference_latency_ms"])),
                        created_at=created_dt
                    ))
                db.add_all(db_txs)
                db.flush()
                db.add_all(db_risks)
                db.commit()
                print(f"  Inserted batch {min(i+batch_size, len(transactions)):,}/{len(transactions):,} transactions...")

            print(f"Inserting {len(scam_reports):,} scam reports and {len(mule_nodes):,} mule graph elements...")
            for sc in scam_reports:
                db.add(ScamReport(
                    id=sc["id"],
                    reporter_id=sc["reporter_id"],
                    reported_account=sc["reported_account"],
                    transaction_id=sc["transaction_id"],
                    reason=sc["reason"],
                    status=ScamReportStatus(sc["status"]),
                    cluster_id=sc["cluster_id"]
                ))
            for mn in mule_nodes:
                db.add(MuleGraphNode(
                    id=mn["id"],
                    account_number=mn["account_number"],
                    cluster_id=mn["cluster_id"],
                    node_type=mn["node_type"],
                    risk_score=Decimal(str(mn["risk_score"])),
                    in_degree=mn["in_degree"],
                    out_degree=mn["out_degree"]
                ))
            for me in mule_edges:
                db.add(MuleGraphEdge(
                    id=me["id"],
                    source_account=me["source_account"],
                    target_account=me["target_account"],
                    cluster_id=me["cluster_id"],
                    total_amount=Decimal(str(me["total_amount"])),
                    transaction_count=me["transaction_count"],
                    is_fan_out=me["is_fan_out"]
                ))
            db.commit()
            print("[OK] Database successfully seeded with full synthetic dataset!")

        except Exception as e:
            db.rollback()
            print(f"[ERROR] Database population failed: {e}")
            raise
        finally:
            db.close()

    def reset_database(self):
        """Safely reset all database tables to clean state."""
        print("Resetting database schema...")
        from scripts.init_db import init_database
        from scripts.seed_baseline import seed_baseline_data
        init_database()
        seed_baseline_data()
        print("[OK] Database reset and reseeded with baseline accounts.")

def main():
    parser = argparse.ArgumentParser(description="upay Pulse Synthetic Data Engine")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand: generate, seed, reset, demo")

    # Command: generate
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic CSV datasets")
    gen_parser.add_argument("--customers", type=int, default=1000, help="Number of customers (default: 1000)")
    gen_parser.add_argument("--agents", type=int, default=50, help="Number of agents (default: 50)")
    gen_parser.add_argument("--transactions", type=int, default=50000, help="Number of transactions (default: 50000)")
    gen_parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    # Command: seed
    seed_parser = subparsers.add_parser("seed", help="Generate and insert synthetic records directly into PostgreSQL")
    seed_parser.add_argument("--customers", type=int, default=1000)
    seed_parser.add_argument("--agents", type=int, default=50)
    seed_parser.add_argument("--transactions", type=int, default=50000)
    seed_parser.add_argument("--batch-size", type=int, default=2000)
    seed_parser.add_argument("--seed", type=int, default=42)

    # Command: reset
    subparsers.add_parser("reset", help="Reset database and seed baseline demo accounts")

    # Command: demo
    subparsers.add_parser("demo", help="Generate compact demo dataset for rapid hackathon testing")

    args = parser.parse_args()
    engine_obj = SyntheticDataEngine(seed=getattr(args, "seed", 42))

    if args.command == "generate":
        engine_obj.generate_all(args.customers, args.agents, args.transactions)
    elif args.command == "seed":
        data = engine_obj.generate_all(args.customers, args.agents, args.transactions)
        engine_obj.seed_database(data, batch_size=args.batch_size)
    elif args.command == "reset":
        engine_obj.reset_database()
    elif args.command == "demo":
        # Fast 1k dataset for quick testing
        data = engine_obj.generate_all(num_customers=150, num_agents=20, num_transactions=2500)
        engine_obj.seed_database(data, batch_size=1000)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
