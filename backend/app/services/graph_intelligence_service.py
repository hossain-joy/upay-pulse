"""
upay Pulse - Graph Intelligence Service
Extracts transaction flows from PostgreSQL, converts to NetworkX topology,
detects money-mule rings, and generates D3/React-Flow graph payloads.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from backend.app.models.transaction import Transaction, TransactionType, TransactionStatus
from backend.app.models.user import User
from backend.app.models.agent import AgentProfile
from backend.app.models.mule_graph import MuleGraphNode, MuleGraphEdge
from ml.graph.mule_detector import MuleGraphDetector

class GraphIntelligenceService:

    @classmethod
    def _records_from_txns(cls, txs: List[Transaction], db: Session) -> tuple[List[Dict[str, Any]], Dict[str, bool]]:
        """
        Maps a list of already-loaded Transaction ORM objects into the
        canonical record dict format expected by MuleGraphDetector. Returns
        `(records, phone_to_frozen)` so callers can annotate nodes with the
        real-time freeze state.

        This helper is shared between the full-graph endpoint
        (`_fetch_transaction_records`) and the time-windowed snapshot builder
        used by the Mule Network Evolution feature. Behaviour of either
        caller is identical to the pre-refactor implementation.
        """
        if not txs:
            return [], {}

        # Collect user IDs to batch-resolve phones/identities
        user_ids = set()
        for t in txs:
            if t.sender_id:
                user_ids.add(t.sender_id)
            if t.receiver_id:
                user_ids.add(t.receiver_id)

        users = db.query(User.id, User.phone, User.email, User.is_frozen).filter(User.id.in_(user_ids)).all()
        id_to_phone = {u.id: (u.phone or u.email) for u in users}
        id_to_frozen = {u.id: u.is_frozen for u in users}
        phone_to_frozen = { (u.phone or u.email): u.is_frozen for u in users }

        # Check agents
        agents = db.query(AgentProfile.user_id, AgentProfile.agent_code).all()
        id_to_agent_code = {a.user_id: a.agent_code for a in agents}

        records = []
        for t in txs:
            s_acc = id_to_phone.get(t.sender_id, "SYSTEM")

            # If receiver is an agent, use agent code if available
            r_acc = id_to_agent_code.get(t.receiver_id) or id_to_phone.get(t.receiver_id, "SYSTEM")

            records.append({
                "sender_account": s_acc,
                "receiver_account": r_acc,
                "amount": float(t.amount),
                "transaction_type": t.transaction_type.value if hasattr(t.transaction_type, 'value') else str(t.transaction_type),
                "agent_id": t.agent_id,
                "created_at": t.created_at.isoformat() if t.created_at else None
            })

        return records, phone_to_frozen

    @classmethod
    def _fetch_transaction_records(cls, db: Session, limit: int = 5000) -> List[Dict[str, Any]]:
        """
        Fetches completed transactions and maps IDs to phone numbers / agent codes
        for human-readable graph topology.
        """
        txs = db.query(Transaction).filter(
            Transaction.status == TransactionStatus.COMPLETED
        ).order_by(desc(Transaction.created_at)).limit(limit).all()

        if not txs:
            return [], {}

        return cls._records_from_txns(txs, db)

    @classmethod
    def get_full_graph(
        cls,
        db: Session,
        cluster_id: Optional[str] = None,
        min_amount: float = 0.0,
        limit: int = 5000
    ) -> Dict[str, Any]:
        """
        Constructs and analyzes the directed transaction graph.
        Can filter by syndicate cluster_id or minimum transfer amount.
        """
        records, phone_to_frozen = cls._fetch_transaction_records(db, limit=limit)
        if not records:
            return {
                "nodes": [],
                "edges": [],
                "clusters": [],
                "summary": {"total_nodes": 0, "total_edges": 0, "mule_nodes_detected": 0, "clusters_detected": 0}
            }

        # Filter by min amount if specified
        if min_amount > 0:
            records = [r for r in records if r["amount"] >= min_amount]

        G = MuleGraphDetector.build_digraph(records)
        analysis = MuleGraphDetector.analyze_graph(G)

        # Annotate nodes with real-time is_frozen status from DB
        for node in analysis["nodes"]:
            node["is_frozen"] = phone_to_frozen.get(node["id"], False)

        # Filter by cluster if requested
        if cluster_id:
            filtered_nodes = [n for n in analysis["nodes"] if n.get("cluster_id") == cluster_id]
            node_ids = {n["id"] for n in filtered_nodes}
            filtered_edges = [e for e in analysis["edges"] if e["source"] in node_ids and e["target"] in node_ids]
            filtered_clusters = [c for c in analysis["clusters"] if c["cluster_id"] == cluster_id]

            return {
                "nodes": filtered_nodes,
                "edges": filtered_edges,
                "clusters": filtered_clusters,
                "summary": {
                    "total_nodes": len(filtered_nodes),
                    "total_edges": len(filtered_edges),
                    "mule_nodes_detected": sum(1 for n in filtered_nodes if "MULE" in n["node_type"]),
                    "clusters_detected": len(filtered_clusters)
                }
            }

        return analysis

    @classmethod
    def get_ego_graph(cls, db: Session, account_identifier: str, radius: int = 2) -> Dict[str, Any]:
        """
        Extracts 1-hop or 2-hop neighborhood ego graph for a targeted suspect or victim.
        """
        # Resolve identifier if it's an email or user ID
        resolved_acc = account_identifier
        user = db.query(User).filter(
            or_(User.phone == account_identifier, User.email == account_identifier, User.id == account_identifier)
        ).first()
        if user and user.phone:
            resolved_acc = user.phone

        records, phone_to_frozen = cls._fetch_transaction_records(db, limit=5000)
        G = MuleGraphDetector.build_digraph(records)
        ego_analysis = MuleGraphDetector.extract_ego_subgraph(G, center_node=resolved_acc, radius=radius)

        if "nodes" in ego_analysis:
            for node in ego_analysis["nodes"]:
                node["is_frozen"] = phone_to_frozen.get(node["id"], False)

        return ego_analysis

    @classmethod
    def get_mule_clusters(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Returns summary of all detected criminal syndicates / mule rings.
        """
        full_graph = cls.get_full_graph(db, limit=5000)
        return full_graph.get("clusters", [])

    @classmethod
    def sync_graph_to_database(cls, db: Session) -> Dict[str, int]:
        """
        Runs graph detection and upserts high-risk nodes and edges into
        `mule_graph_nodes` and `mule_graph_edges` tables for persistent reporting.
        """
        full_graph = cls.get_full_graph(db, limit=5000)
        nodes = full_graph.get("nodes", [])
        edges = full_graph.get("edges", [])

        # Filter only suspicious/mule/agent nodes or nodes in clusters
        mule_nodes = [n for n in nodes if n["risk_score"] >= 0.50 or n.get("cluster_id")]
        
        # Clear existing entries
        db.query(MuleGraphNode).delete()
        db.query(MuleGraphEdge).delete()
        db.flush()

        # Insert Nodes
        for n in mule_nodes:
            db_node = MuleGraphNode(
                account_number=n["id"],
                cluster_id=n.get("cluster_id"),
                node_type=n["node_type"],
                risk_score=Decimal(str(n["risk_score"])),
                in_degree=n["in_degree"],
                out_degree=n["out_degree"],
                is_frozen=n.get("is_frozen", False)
            )
            db.add(db_node)

        # Insert Edges
        synced_edges = 0
        node_id_set = {n["id"] for n in mule_nodes}
        for e in edges:
            if e["source"] in node_id_set or e["target"] in node_id_set:
                db_edge = MuleGraphEdge(
                    source_account=e["source"],
                    target_account=e["target"],
                    cluster_id=e.get("cluster_id"),
                    total_amount=Decimal(str(e["amount"])),
                    transaction_count=e["tx_count"],
                    is_fan_out=(e.get("tx_count", 0) > 1 or e.get("amount", 0) > 10000)
                )
                db.add(db_edge)
                synced_edges += 1

        db.commit()

        return {
            "nodes_synced": len(mule_nodes),
            "edges_synced": synced_edges,
            "clusters_detected": len(full_graph.get("clusters", []))
        }
