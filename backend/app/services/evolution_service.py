"""
upay Pulse — Mule Network Evolution Service (Phase-3 visualization feature).

Builds time-windowed snapshots of the existing MuleGraphDetector pipeline so
the Risk Console can show how the mule network evolves week-by-week.

This service reuses Phase-2 code verbatim:
  - backend.app.services.graph_intelligence_service.GraphIntelligenceService
  - ml.graph.mule_detector.MuleGraphDetector

It introduces NO new graph logic — only derives datasets from the existing
Transaction.created_at timestamps, runs the existing pipeline per window,
and computes set-algebra diffs between two snapshots.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.exceptions import AppException
from backend.app.models.transaction import Transaction, TransactionStatus
from backend.app.services.graph_intelligence_service import GraphIntelligenceService
from ml.graph.mule_detector import MuleGraphDetector


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ALLOWED_BUCKET_DAYS: Tuple[Optional[int], ...] = (1, 3, 7, 14, 30, None)
"""None is accepted as "single window covering the whole range" for power-users."""

DEFAULT_BUCKET_DAYS: int = 7
"""Weekly buckets → ~14 datasets across the 91-day synthetic window."""

DEFAULT_SNAPSHOT_LIMIT: int = 5000
"""Per-window cap to bound the NetworkX in-memory graph size."""

DEFAULT_TOP_N: int = 100
"""Default cap on nodes returned per snapshot (for animation perf)."""

RISK_CHANGE_THRESHOLD: float = 0.05
"""|delta risk_score| must exceed this to count as a meaningful change."""

CLUSTER_OVERLAP_THRESHOLD: float = 0.80
"""Jaccard membership overlap below this counts as a cluster change."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class EvolutionService:
    """Time-windowed snapshot builder + diff/emerging-mule analysis."""

    # ----- 1. Dataset derivation -------------------------------------------

    @staticmethod
    def _coerce_bucket_days(bucket_days: Optional[int]) -> int:
        if bucket_days is None:
            return 1_000_000  # effectively a single window
        if bucket_days not in ALLOWED_BUCKET_DAYS:
            raise AppException(
                f"bucket_days must be one of {[d for d in ALLOWED_BUCKET_DAYS if d is not None]}; got {bucket_days}.",
                code="INVALID_BUCKET_DAYS",
                status_code=422,
            )
        return bucket_days

    @staticmethod
    def _derive_datasets(db: Session, bucket_days: int) -> List[Dict[str, Any]]:
        """
        Compute chronological, non-overlapping dataset buckets over the
        full window of COMPLETED transactions.

        Each row: { id, start, end, tx_count, label }.
        The last bucket is closed at the upper bound so the trailing partial
        bucket still appears.
        """
        span = (
            db.query(func.min(Transaction.created_at), func.max(Transaction.created_at))
            .filter(Transaction.status == TransactionStatus.COMPLETED)
            .one()
        )
        start_raw, end_raw = span[0], span[1]
        if start_raw is None or end_raw is None:
            return []

        # Normalize to UTC-naive datetimes so we can iterate cleanly with timedelta
        start = start_raw.replace(tzinfo=None) if start_raw.tzinfo else start_raw
        end = end_raw.replace(tzinfo=None) if end_raw.tzinfo else end_raw

        datasets: List[Dict[str, Any]] = []
        cursor = start
        i = 1
        while cursor < end:
            b_end = min(cursor + timedelta(days=bucket_days), end)
            cnt = (
                db.query(Transaction)
                .filter(
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= cursor,
                    Transaction.created_at < b_end,
                )
                .count()
            )
            label = f"{cursor.strftime('%b %d')} – {b_end.strftime('%b %d')}"
            datasets.append(
                {
                    "id": f"W{i:02d}",
                    "start": cursor.isoformat(),
                    "end": b_end.isoformat(),
                    "tx_count": cnt,
                    "label": label,
                }
            )
            cursor = b_end
            i += 1
        return datasets

    @classmethod
    def list_datasets(cls, db: Session, bucket_days: Optional[int] = DEFAULT_BUCKET_DAYS) -> Dict[str, Any]:
        bd = cls._coerce_bucket_days(bucket_days)
        datasets = cls._derive_datasets(db, bd)

        span = (
            db.query(func.min(Transaction.created_at), func.max(Transaction.created_at))
            .filter(Transaction.status == TransactionStatus.COMPLETED)
            .one()
        )
        return {
            "bucket_days": bd if bd != 1_000_000 else None,
            "window_start": span[0].isoformat() if span[0] else None,
            "window_end": span[1].isoformat() if span[1] else None,
            "datasets": datasets,
        }

    # ----- 2. Snapshot computation ----------------------------------------

    @classmethod
    def _build_snapshot(
        cls,
        db: Session,
        start: datetime,
        end: datetime,
    ) -> Dict[str, Any]:
        txs = (
            db.query(Transaction)
            .filter(
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= start,
                Transaction.created_at < end,
            )
            .order_by(Transaction.created_at.asc())
            .limit(DEFAULT_SNAPSHOT_LIMIT)
            .all()
        )
        records, phone_to_frozen = GraphIntelligenceService._records_from_txns(txs, db)
        G = MuleGraphDetector.build_digraph(records)
        analysis = MuleGraphDetector.analyze_graph(G)
        for n in analysis["nodes"]:
            n["is_frozen"] = phone_to_frozen.get(n["id"], False)
        return analysis

    @classmethod
    def _apply_top_n(cls, snapshot: Dict[str, Any], top_n: int) -> Dict[str, Any]:
        """Cap the nodes array to top-N by risk_score for animation perf.

        Edges/clusters/summary are returned unfiltered so the diff engine
        still sees the full graph; the frontend simply renders fewer nodes.
        """
        if top_n is None or top_n <= 0:
            return snapshot
        if len(snapshot["nodes"]) <= top_n:
            return snapshot

        ranked = sorted(snapshot["nodes"], key=lambda n: n["risk_score"], reverse=True)[:top_n]
        kept_ids = {n["id"] for n in ranked}
        kept_edges = [e for e in snapshot["edges"] if e["source"] in kept_ids and e["target"] in kept_ids]
        summary = dict(snapshot.get("summary", {}))
        summary["total_nodes"] = len(ranked)
        summary["total_edges"] = len(kept_edges)
        summary["mule_nodes_detected"] = sum(1 for n in ranked if "MULE" in n["node_type"])
        summary["rendered_top_n"] = top_n

        return {
            "nodes": ranked,
            "edges": kept_edges,
            "clusters": snapshot.get("clusters", []),
            "summary": summary,
        }

    @classmethod
    def get_snapshot(
        cls,
        db: Session,
        dataset_id: str,
        bucket_days: Optional[int] = DEFAULT_BUCKET_DAYS,
        top_n: int = DEFAULT_TOP_N,
    ) -> Dict[str, Any]:
        bd = cls._coerce_bucket_days(bucket_days)
        datasets = cls._derive_datasets(db, bd)
        match = next((d for d in datasets if d["id"] == dataset_id), None)
        if match is None:
            raise AppException(
                f"Dataset {dataset_id!r} not found for bucket_days={bd}.",
                code="DATASET_NOT_FOUND",
                status_code=404,
            )

        analysis = cached_get_snapshot(db, bd, match["start"], match["end"])
        rendered = cls._apply_top_n(analysis, top_n)

        return {
            "dataset_id": dataset_id,
            "start": match["start"],
            "end": match["end"],
            "label": match["label"],
            "tx_count": match["tx_count"],
            "bucket_days": bd if bd != 1_000_000 else None,
            "nodes": rendered["nodes"],
            "edges": rendered["edges"],
            "clusters": rendered["clusters"],
            "summary": rendered["summary"],
        }

    # ----- 3. Diff computation --------------------------------------------

    @staticmethod
    def diff_snapshots(prev: Dict[str, Any], curr: Dict[str, Any]) -> Dict[str, Any]:
        prev_nodes = {n["id"]: n for n in prev["nodes"]}
        curr_nodes = {n["id"]: n for n in curr["nodes"]}

        new_nodes = [curr_nodes[i] for i in curr_nodes.keys() - prev_nodes.keys()]
        removed_nodes = [prev_nodes[i] for i in prev_nodes.keys() - curr_nodes.keys()]

        # Edges: frozenset so reversed direction is NOT a "new" edge.
        def _edge_set(edges: List[Dict[str, Any]]):
            out = {}
            for e in edges:
                key = frozenset((e["source"], e["target"]))
                if key not in out:
                    out[key] = e
            return out

        pe = _edge_set(prev["edges"])
        ce = _edge_set(curr["edges"])
        new_edges = [ce[k] for k in ce.keys() - pe.keys()]
        removed_edges = [pe[k] for k in pe.keys() - ce.keys()]

        risk_up: List[Dict[str, Any]] = []
        risk_down: List[Dict[str, Any]] = []
        for nid in prev_nodes.keys() & curr_nodes.keys():
            prev_r = float(prev_nodes[nid].get("risk_score", 0.0) or 0.0)
            curr_r = float(curr_nodes[nid].get("risk_score", 0.0) or 0.0)
            delta = round(curr_r - prev_r, 3)
            if delta > RISK_CHANGE_THRESHOLD:
                risk_up.append({
                    "id": nid,
                    "label": curr_nodes[nid].get("label", nid),
                    "from": prev_r,
                    "to": curr_r,
                    "delta": delta,
                })
            elif delta < -RISK_CHANGE_THRESHOLD:
                risk_down.append({
                    "id": nid,
                    "label": curr_nodes[nid].get("label", nid),
                    "from": prev_r,
                    "to": curr_r,
                    "delta": delta,
                })

        # Cluster changes: same id, membership overlap < threshold.
        pc = {c["cluster_id"]: set(c["nodes"]) for c in prev.get("clusters", [])}
        cc = {c["cluster_id"]: set(c["nodes"]) for c in curr.get("clusters", [])}
        cluster_changes: List[Dict[str, Any]] = []
        for cid in pc.keys() & cc.keys():
            old, new = pc[cid], cc[cid]
            union = old | new
            overlap = (len(old & new) / len(union)) if union else 1.0
            if overlap < CLUSTER_OVERLAP_THRESHOLD:
                cluster_changes.append({
                    "cluster_id": cid,
                    "overlap": round(overlap, 3),
                    "added": sorted(list(new - old)),
                    "removed": sorted(list(old - new)),
                })

        return {
            "new_nodes": new_nodes,
            "removed_nodes": removed_nodes,
            "new_edges": new_edges,
            "removed_edges": removed_edges,
            "risk_up": risk_up,
            "risk_down": risk_down,
            "cluster_changes": cluster_changes,
            "stats": {
                "new_nodes_count": len(new_nodes),
                "removed_nodes_count": len(removed_nodes),
                "new_edges_count": len(new_edges),
                "removed_edges_count": len(removed_edges),
                "risk_up_count": len(risk_up),
                "risk_down_count": len(risk_down),
                "cluster_changes_count": len(cluster_changes),
            },
        }

    @classmethod
    def get_diff(
        cls,
        db: Session,
        dataset_id: str,
        from_dataset_id: str,
        bucket_days: Optional[int] = DEFAULT_BUCKET_DAYS,
        top_n: int = DEFAULT_TOP_N,
    ) -> Dict[str, Any]:
        prev = cls.get_snapshot(db, from_dataset_id, bucket_days, top_n=top_n)
        curr = cls.get_snapshot(db, dataset_id, bucket_days, top_n=top_n)
        diff = cls.diff_snapshots(prev, curr)
        return {
            "from": from_dataset_id,
            "to": dataset_id,
            "bucket_days": cls._coerce_bucket_days(bucket_days),
            **diff,
        }

    # ----- 4. Emerging mules -----------------------------------------------

    @staticmethod
    def emerging_mules(prev: Dict[str, Any], curr: Dict[str, Any]) -> Dict[str, Any]:
        prev_nodes = {n["id"]: n for n in prev["nodes"]}
        mules = []
        for n in curr["nodes"]:
            if "MULE" not in n.get("node_type", ""):
                continue
            nid = n["id"]
            prev_n = prev_nodes.get(nid)
            if prev_n is None:
                mules.append({
                    "id": nid,
                    "label": n.get("label", nid),
                    "node_type": n["node_type"],
                    "risk_score": n["risk_score"],
                    "emergence": "newly_classified",
                    "previous_risk": None,
                    "cluster_id": n.get("cluster_id"),
                })
            else:
                prev_r = float(prev_n.get("risk_score", 0.0) or 0.0)
                curr_r = float(n.get("risk_score", 0.0) or 0.0)
                if prev_r <= 0.40 and curr_r >= 0.70:
                    mules.append({
                        "id": nid,
                        "label": n.get("label", nid),
                        "node_type": n["node_type"],
                        "risk_score": curr_r,
                        "emergence": "risk_escalated",
                        "previous_risk": prev_r,
                        "cluster_id": n.get("cluster_id"),
                    })
        return {"count": len(mules), "mules": mules}

    @classmethod
    def get_emerging(
        cls,
        db: Session,
        dataset_id: str,
        from_dataset_id: str,
        bucket_days: Optional[int] = DEFAULT_BUCKET_DAYS,
        top_n: int = DEFAULT_TOP_N,
    ) -> Dict[str, Any]:
        prev = cls.get_snapshot(db, from_dataset_id, bucket_days, top_n=top_n)
        curr = cls.get_snapshot(db, dataset_id, bucket_days, top_n=top_n)
        out = cls.emerging_mules(prev, curr)
        return {
            "from": from_dataset_id,
            "to": dataset_id,
            **out,
        }


# Module-level snapshot cache (process lifetime). Keyed by (bucket_days, start, end).
# Bounded by FIFO eviction at _SNAPSHOT_CACHE_MAX entries.
_SNAPSHOT_CACHE: Dict[Tuple[Optional[int], str, str], Dict[str, Any]] = {}
_SNAPSHOT_CACHE_MAX = 64


def _cache_key(bucket_days: Optional[int], start_iso: str, end_iso: str) -> Tuple[Optional[int], str, str]:
    return (bucket_days, start_iso, end_iso)


def cached_get_snapshot(
    db: Session,
    bucket_days: Optional[int],
    start_iso: str,
    end_iso: str,
) -> Dict[str, Any]:
    """Return a cached snapshot if present, else compute and cache it.

    Used by `get_snapshot`/`get_diff`/`get_emerging` to avoid re-running the
    NetworkX pipeline on every endpoint hit. The cache is in-process and
    bounded to `_SNAPSHOT_CACHE_MAX` entries with FIFO eviction.
    """
    key = _cache_key(bucket_days, start_iso, end_iso)
    if key in _SNAPSHOT_CACHE:
        return _SNAPSHOT_CACHE[key]
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    snap = EvolutionService._build_snapshot(db, start, end)
    if len(_SNAPSHOT_CACHE) >= _SNAPSHOT_CACHE_MAX:
        try:
            first_key = next(iter(_SNAPSHOT_CACHE))
            _SNAPSHOT_CACHE.pop(first_key, None)
        except StopIteration:
            pass
    _SNAPSHOT_CACHE[key] = snap
    return snap