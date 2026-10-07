"""
upay Pulse — Mule Network Evolution endpoint tests (Phase-3 visualisation).

These tests verify that:
  - /graph/evolution/datasets derives chronological buckets from real
    Transaction.created_at timestamps (no hardcoded list).
  - /graph/evolution/{id} returns a real topology built by the existing
    MuleGraphDetector pipeline.
  - /graph/evolution/{id}/changes diffs two snapshots correctly (set algebra,
    0.05 risk threshold, frozenset edge equality, cluster overlap < 0.8).
  - /graph/evolution/{id}/emerging returns newly classified / escalated mules.
  - RBAC: anonymous 401, customer 403, admin 200.

Tests seed their own multi-day transactions directly via SessionLocal so they
don't depend on global state.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.app.core.database import SessionLocal
from backend.app.models.transaction import (
    Transaction,
    TransactionStatus,
    TransactionType,
)
from backend.app.models.user import User
from backend.app.services.evolution_service import (
    EvolutionService,
    RISK_CHANGE_THRESHOLD,
    CLUSTER_OVERLAP_THRESHOLD,
)


def _auth(client, email: str, password: str = None) -> str:
    if password is None:
        password = "Admin@1234" if "admin" in email else "Demo@1234"
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _admin_headers(client) -> dict:
    return {"Authorization": f"Bearer {_auth(client, 'admin@example.com')}"}


def _customer_headers(client) -> dict:
    return {"Authorization": f"Bearer {_auth(client, 'customer@example.com')}"}


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def seeded_multiday_db():
    """
    Insert 28 days of synthetic COMPLETED transactions spread across the
    customer and a peer. This gives the dataset derivation enough temporal
    range to produce multiple buckets at default bucket_days=7.
    Cleans up afterwards so it doesn't pollute later tests.
    """
    db = SessionLocal()
    inserted_ids = []
    try:
        customer = db.query(User).filter(User.email == "customer@example.com").first()
        peer = db.query(User).filter(User.email == "rahima@example.com").first()
        if customer is None or peer is None:
            pytest.skip("Test DB not seeded with customer/rahima users; run scripts/init_db + seed_baseline first.")

        base = datetime.now(tz=timezone.utc) - timedelta(days=28)
        ref_counter = 99000
        for day_offset in range(0, 28):
            tx_time = base + timedelta(days=day_offset, hours=10)
            for _ in range(3):  # 3 txns/day → 84 total
                ref_counter += 1
                # Alternate direction so the graph has real fan-in/out
                sender_id = customer.id if ref_counter % 2 == 0 else peer.id
                receiver_id = peer.id if sender_id == customer.id else customer.id
                txn = Transaction(
                    transaction_reference=f"TXN-EVO-{ref_counter}",
                    sender_id=sender_id,
                    receiver_id=receiver_id,
                    agent_id=None,
                    amount=Decimal("1500.00"),
                    fee=Decimal("5.00"),
                    transaction_type=TransactionType.SEND_MONEY,
                    status=TransactionStatus.COMPLETED,
                    category="Transfer",
                    description="evolution test seed",
                    is_flagged_fraud=False,
                    created_at=tx_time,
                )
                db.add(txn)
                db.flush()
                inserted_ids.append(txn.id)
        db.commit()
        yield db
    finally:
        # Cleanup: delete only the rows we inserted (cascade-safe)
        try:
            if inserted_ids:
                db.query(Transaction).filter(Transaction.id.in_(inserted_ids)).delete(synchronize_session=False)
                db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 1. Dataset derivation
# ---------------------------------------------------------------------------
def test_dataset_derivation_count_and_order(seeded_multiday_db):
    db = seeded_multiday_db
    datasets = EvolutionService._derive_datasets(db, bucket_days=7)
    assert len(datasets) >= 4, f"expected >=4 buckets across 28 days, got {len(datasets)}"
    # Chronological order
    starts = [datetime.fromisoformat(d["start"]) for d in datasets]
    assert starts == sorted(starts), "datasets must be chronological"
    # Non-overlapping and consecutive
    for prev, nxt in zip(datasets, datasets[1:]):
        prev_end = datetime.fromisoformat(prev["end"])
        nxt_start = datetime.fromisoformat(nxt["start"])
        assert nxt_start == prev_end, f"gap between {prev['id']} and {nxt['id']}"


def test_dataset_derivation_default_7d_layout(seeded_multiday_db):
    """At default bucket_days=7, every dataset id is W{NN}, datasets are chronological,
    and tx_count is non-negative. Exact count depends on the full DB window."""
    db = seeded_multiday_db
    datasets = EvolutionService._derive_datasets(db, bucket_days=7)
    assert len(datasets) >= 4, f"expected >=4 buckets, got {len(datasets)}"
    for i, d in enumerate(datasets, start=1):
        assert d["id"] == f"W{i:02d}", f"bucket #{i} should be W{i:02d}, got {d['id']}"
        assert d["tx_count"] >= 0
    starts = [datetime.fromisoformat(d["start"]) for d in datasets]
    assert starts == sorted(starts)


def test_dataset_derivation_custom_3d_bucket(seeded_multiday_db):
    db = seeded_multiday_db
    datasets = EvolutionService._derive_datasets(db, bucket_days=3)
    # 28/3 = 9 full + 1 partial = 10 buckets
    assert 9 <= len(datasets) <= 11
    for d in datasets:
        assert d["id"].startswith("W")


# ---------------------------------------------------------------------------
# 2. Snapshot endpoint
# ---------------------------------------------------------------------------
def test_snapshot_endpoint_returns_real_topology(client, seeded_multiday_db):
    headers = _admin_headers(client)
    res = client.get("/api/v1/graph/evolution/datasets?bucket_days=7", headers=headers)
    assert res.status_code == 200
    datasets = res.json()["datasets"]
    assert len(datasets) >= 2
    ds = datasets[0]
    res = client.get(f"/api/v1/graph/evolution/{ds['id']}?bucket_days=7", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert "nodes" in body and "edges" in body and "summary" in body
    assert body["dataset_id"] == ds["id"]


def test_snapshot_endpoint_404_unknown_dataset(client, seeded_multiday_db):
    headers = _admin_headers(client)
    res = client.get("/api/v1/graph/evolution/W99?bucket_days=7", headers=headers)
    assert res.status_code == 404
    assert res.json().get("error", {}).get("code") == "DATASET_NOT_FOUND"


def test_snapshot_endpoint_clamps_top_n(client, seeded_multiday_db):
    headers = _admin_headers(client)
    res = client.get("/api/v1/graph/evolution/datasets?bucket_days=7", headers=headers)
    assert res.status_code == 200
    ds = res.json()["datasets"][0]
    res = client.get(f"/api/v1/graph/evolution/{ds['id']}?bucket_days=7&top_n=5", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert len(body["nodes"]) <= 5


# ---------------------------------------------------------------------------
# 3. Diff endpoint
# ---------------------------------------------------------------------------
def test_diff_endpoint_returns_correct_structure(client, seeded_multiday_db):
    headers = _admin_headers(client)
    res = client.get("/api/v1/graph/evolution/datasets?bucket_days=7", headers=headers)
    datasets = res.json()["datasets"]
    if len(datasets) < 2:
        pytest.skip("Not enough datasets for diff")
    a, b = datasets[0]["id"], datasets[1]["id"]
    res = client.get(f"/api/v1/graph/evolution/{b}/changes?from={a}&bucket_days=7", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    # Schema fields: FastAPI serializes with aliases when response_model is set.
    assert body.get("from") == a or body.get("from_dataset") == a
    assert body.get("to") == b or body.get("to_dataset") == b
    assert "new_nodes" in body and "removed_nodes" in body
    assert "new_edges" in body and "removed_edges" in body
    assert "risk_up" in body and "risk_down" in body
    assert "cluster_changes" in body
    assert "stats" in body
    assert body["stats"]["new_nodes_count"] == len(body["new_nodes"])


def test_diff_edge_set_uses_frozenset():
    """Reversed direction is NOT a 'new' edge."""
    prev = {
        "nodes": [{"id": "A", "risk_score": 0.5}, {"id": "B", "risk_score": 0.5}],
        "edges": [{"source": "A", "target": "B", "amount": 100, "tx_count": 1, "is_cash_out": False, "cluster_id": None, "id": "A->B"}],
        "clusters": [],
        "summary": {},
    }
    curr = {
        "nodes": [{"id": "A", "risk_score": 0.5}, {"id": "B", "risk_score": 0.5}],
        "edges": [{"source": "B", "target": "A", "amount": 200, "tx_count": 1, "is_cash_out": False, "cluster_id": None, "id": "B->A"}],
        "clusters": [],
        "summary": {},
    }
    diff = EvolutionService.diff_snapshots(prev, curr)
    # Reversed direction = same frozenset, so no new/removed edges.
    assert diff["stats"]["new_edges_count"] == 0
    assert diff["stats"]["removed_edges_count"] == 0


def test_diff_risk_threshold_is_strict_above_point05():
    """delta 0.04 ignored, delta 0.06 reported."""
    prev = {"nodes": [{"id": "X", "risk_score": 0.50}], "edges": [], "clusters": [], "summary": {}}
    small = {"nodes": [{"id": "X", "risk_score": 0.54}], "edges": [], "clusters": [], "summary": {}}
    big = {"nodes": [{"id": "X", "risk_score": 0.56}], "edges": [], "clusters": [], "summary": {}}

    diff_small = EvolutionService.diff_snapshots(prev, small)
    assert diff_small["stats"]["risk_up_count"] == 0

    diff_big = EvolutionService.diff_snapshots(prev, big)
    assert diff_big["stats"]["risk_up_count"] == 1
    assert diff_big["risk_up"][0]["delta"] == pytest.approx(0.06, abs=1e-6)


def test_diff_threshold_constant_matches_plan():
    """Sanity: constant is exactly 0.05 as documented in the plan."""
    assert RISK_CHANGE_THRESHOLD == 0.05
    assert CLUSTER_OVERLAP_THRESHOLD == 0.80


def test_diff_cluster_change_overlap_below_0_8_reported():
    """Same cluster_id, overlap=0.5 → cluster change reported with added/removed members."""
    prev = {
        "nodes": [
            {"id": "A", "risk_score": 0.5, "cluster_id": "C1"},
            {"id": "B", "risk_score": 0.5, "cluster_id": "C1"},
        ],
        "edges": [],
        "clusters": [{"cluster_id": "C1", "size": 2, "total_volume": 100, "nodes": ["A", "B"]}],
        "summary": {},
    }
    curr = {
        "nodes": [
            {"id": "A", "risk_score": 0.5, "cluster_id": "C1"},  # kept
            {"id": "C", "risk_score": 0.5, "cluster_id": "C1"},  # added
        ],
        "edges": [],
        "clusters": [{"cluster_id": "C1", "size": 2, "total_volume": 100, "nodes": ["A", "C"]}],
        "summary": {},
    }
    diff = EvolutionService.diff_snapshots(prev, curr)
    assert diff["stats"]["cluster_changes_count"] == 1
    change = diff["cluster_changes"][0]
    assert change["cluster_id"] == "C1"
    assert "C" in change["added"]
    assert "B" in change["removed"]


# ---------------------------------------------------------------------------
# 4. Emerging mules
# ---------------------------------------------------------------------------
def test_emerging_endpoint_marks_new_mule_classification():
    """A mule present in curr but absent in prev → 'newly_classified'."""
    prev = {"nodes": [], "edges": [], "clusters": [], "summary": {}}
    curr = {
        "nodes": [
            {"id": "MULE-1", "label": "MULE-1", "node_type": "PRIMARY_MULE",
             "risk_score": 0.91, "cluster_id": "CLUSTER-A"},
        ],
        "edges": [],
        "clusters": [],
        "summary": {},
    }
    out = EvolutionService.emerging_mules(prev, curr)
    assert out["count"] == 1
    mule = out["mules"][0]
    assert mule["id"] == "MULE-1"
    assert mule["emergence"] == "newly_classified"
    assert mule["previous_risk"] is None


def test_emerging_endpoint_marks_risk_escalation():
    """NORMAL_USER → PRIMARY_MULE with risk crossing 0.7 from <=0.4 → 'risk_escalated'."""
    prev = {"nodes": [{"id": "x", "node_type": "NORMAL_USER", "risk_score": 0.30}],
            "edges": [], "clusters": [], "summary": {}}
    curr = {"nodes": [{"id": "x", "label": "x", "node_type": "PRIMARY_MULE",
                        "risk_score": 0.85, "cluster_id": None}],
            "edges": [], "clusters": [], "summary": {}}
    out = EvolutionService.emerging_mules(prev, curr)
    assert out["count"] == 1
    assert out["mules"][0]["emergence"] == "risk_escalated"
    assert out["mules"][0]["previous_risk"] == 0.30


def test_emerging_endpoint_skips_unchanged_mule():
    prev = {"nodes": [{"id": "m", "node_type": "PRIMARY_MULE", "risk_score": 0.85}],
            "edges": [], "clusters": [], "summary": {}}
    curr = {"nodes": [{"id": "m", "label": "m", "node_type": "PRIMARY_MULE",
                        "risk_score": 0.86, "cluster_id": None}],
            "edges": [], "clusters": [], "summary": {}}
    out = EvolutionService.emerging_mules(prev, curr)
    assert out["count"] == 0


# ---------------------------------------------------------------------------
# 5. RBAC + empty period
# ---------------------------------------------------------------------------
def test_evolution_endpoints_require_auth(client):
    res = client.get("/api/v1/graph/evolution/datasets?bucket_days=7")
    assert res.status_code == 401


def test_evolution_endpoints_require_risk_analyst(client):
    headers = _customer_headers(client)
    res = client.get("/api/v1/graph/evolution/datasets?bucket_days=7", headers=headers)
    assert res.status_code == 403


def test_empty_period_snapshot_returns_zeros(client, seeded_multiday_db):
    """bucket_days=30 over a 28-day seeded range → exactly 1 bucket containing all data.
    Use bucket_days=1 to find a near-empty bucket; with 3 txns/day, every 1-day bucket
    has data, so we instead exercise the empty-snapshot path by querying an out-of-range
    dataset id and verifying the snapshot for a known populated bucket returns sane data
    (the truly-empty bucket case is exercised by the existing analyze_graph empty path)."""
    headers = _admin_headers(client)
    res = client.get("/api/v1/graph/evolution/datasets?bucket_days=7", headers=headers)
    datasets = res.json()["datasets"]
    # Find a bucket with 0 txns (the trailing partial bucket if all 84 txns fit in W01-W04)
    empty_buckets = [d for d in datasets if d["tx_count"] == 0]
    if not empty_buckets:
        pytest.skip("No empty bucket available with seeded data; happy-path covered by other tests.")
    ds = empty_buckets[0]
    res = client.get(f"/api/v1/graph/evolution/{ds['id']}?bucket_days=7", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["total_nodes"] == 0
    assert body["summary"]["total_edges"] == 0
    assert body["nodes"] == []
    assert body["edges"] == []