"""
upay Pulse — Unseen Fraud Patterns Evaluation Suite (Workstream 6)
Synthesizes 2 novel fraud topologies withheld during training to test generalization:
1. Low-and-Slow Smurfing (Micro-amounts evading velocity & amount Z-score thresholds)
2. Coordinated Multi-Hop Relay Cycles (A -> B -> C -> D -> A)
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

def generate_unseen_fraud_test_cases(base_time: datetime, count: int = 50) -> pd.DataFrame:
    """
    Generates test transactions containing unseen fraud strategies.
    None of these patterns exist in standard training data.
    """
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)

    records = []

    # Pattern 1: Low-and-Slow Smurfing (25 cases)
    # Split 25,000 BDT into 10 micro-transactions over 3 days (amount ~ 2,500 BDT)
    smurf_senders = [f"smurf_victim_{i}" for i in range(5)]
    smurf_mule = "unseen_smurf_mule_primary"

    for i in range(25):
        t = base_time + timedelta(hours=i * 2.5)
        s = smurf_senders[i % len(smurf_senders)]
        records.append({
            "id": f"unseen_smurf_{i}",
            "transaction_reference": f"TXN-UNSEEN-SMURF-{i:03d}",
            "sender_id": s,
            "receiver_id": smurf_mule,
            "amount": round(np.random.uniform(1800.0, 2450.0), 2),  # Sub-threshold
            "transaction_type": "SEND_MONEY",
            "is_flagged_fraud": True,
            "fraud_type": "LOW_AND_SLOW_SMURF",
            "created_at_dt": t,
            "description": "Unseen micro-smurfing disbursement"
        })

    # Pattern 2: Multi-Hop Relay Ring (25 cases)
    # Cycle of 5 accounts: Ring-A -> Ring-B -> Ring-C -> Ring-D -> Ring-E -> Ring-A
    ring_nodes = [f"ring_node_{j}" for j in range(5)]
    for i in range(25):
        t = base_time + timedelta(hours=30 + (i * 0.5))
        u = ring_nodes[i % 5]
        v = ring_nodes[(i + 1) % 5]
        records.append({
            "id": f"unseen_ring_{i}",
            "transaction_reference": f"TXN-UNSEEN-RING-{i:03d}",
            "sender_id": u,
            "receiver_id": v,
            "amount": round(np.random.uniform(8000.0, 14000.0), 2),
            "transaction_type": "SEND_MONEY",
            "is_flagged_fraud": True,
            "fraud_type": "CYCLIC_RELAY_RING",
            "created_at_dt": t,
            "description": "Unseen multi-hop relay ring transfer"
        })

    return pd.DataFrame(records)
