"""
upay Pulse - SecurityAI: Money-Mule Graph Intelligence Engine
Uses NetworkX to analyze transaction topology, detect fan-out hubs,
convergence exit agents, and isolated syndicate clusters.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict
from datetime import datetime
import networkx as nx

class MuleGraphDetector:
    """
    Analyzes directed transaction graphs to identify money-mule rings,
    fan-out disbursement nodes, and cash-out convergence bottlenecks.
    """

    def __init__(self):
        pass

    @staticmethod
    def build_digraph(transactions: List[Dict[str, Any]]) -> nx.DiGraph:
        """
        Builds a directed multigraph / weighted DiGraph from transaction records.
        Each node represents an account identifier (phone, agent_code, or user_id).
        Edges represent directed aggregate fund transfers.
        """
        G = nx.DiGraph()

        for tx in transactions:
            sender = str(tx.get("sender_account") or tx.get("sender_id") or "UNKNOWN_SENDER")
            receiver = str(tx.get("receiver_account") or tx.get("receiver_id") or "UNKNOWN_RECEIVER")
            amount = float(tx.get("amount", 0.0))
            is_cash_out = (tx.get("transaction_type") == "CASH_OUT")
            created_at = tx.get("created_at")

            if not G.has_node(sender):
                G.add_node(sender, total_sent=0.0, total_received=0.0, tx_count=0, is_agent=False)
            if not G.has_node(receiver):
                is_rcv_agent = bool(tx.get("agent_id") or "AGT" in receiver)
                G.add_node(receiver, total_sent=0.0, total_received=0.0, tx_count=0, is_agent=is_rcv_agent)

            # Update node aggregates
            G.nodes[sender]["total_sent"] += amount
            G.nodes[sender]["tx_count"] += 1
            G.nodes[receiver]["total_received"] += amount
            G.nodes[receiver]["tx_count"] += 1

            # Update or create edge
            if G.has_edge(sender, receiver):
                G[sender][receiver]["weight"] += amount
                G[sender][receiver]["tx_count"] += 1
                if is_cash_out:
                    G[sender][receiver]["is_cash_out"] = True
            else:
                G.add_edge(
                    sender,
                    receiver,
                    weight=amount,
                    tx_count=1,
                    is_cash_out=is_cash_out,
                    first_tx=created_at,
                    last_tx=created_at
                )

        return G

    @classmethod
    def analyze_graph(cls, G: nx.DiGraph) -> Dict[str, Any]:
        """
        Computes node centrality, in/out degrees, and detects mule patterns.
        Returns classified nodes, edges, and detected syndicates.
        """
        if G.number_of_nodes() == 0:
            return {
                "nodes": [],
                "edges": [],
                "clusters": [],
                "summary": {
                    "total_nodes": 0,
                    "total_edges": 0,
                    "mule_nodes_detected": 0,
                    "clusters_detected": 0
                }
            }

        # Degree calculations
        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())
        
        # Centrality metrics
        try:
            pagerank = nx.pagerank(G, weight="weight", max_iter=100)
        except Exception:
            pagerank = {n: 1.0 / len(G) for n in G.nodes()}

        # Weakly connected components to isolate clusters
        components = list(nx.weakly_connected_components(G))
        node_to_cluster = {}
        clusters_info = []

        for c_idx, comp in enumerate(components):
            c_name = f"CLUSTER-{c_idx+1:03d}"
            comp_nodes = list(comp)
            total_vol = sum(G.nodes[n]["total_sent"] for n in comp_nodes)
            
            # Record cluster assignment
            for n in comp_nodes:
                node_to_cluster[n] = c_name

            if len(comp_nodes) >= 3:
                clusters_info.append({
                    "cluster_id": c_name,
                    "size": len(comp_nodes),
                    "total_volume": round(total_vol, 2),
                    "nodes": comp_nodes
                })

        # Classify Node Roles & Calculate Mule Risk Score
        classified_nodes = []
        mule_count = 0

        for node_id in G.nodes():
            n_data = G.nodes[node_id]
            in_deg = in_degrees.get(node_id, 0)
            out_deg = out_degrees.get(node_id, 0)
            sent = n_data.get("total_sent", 0.0)
            received = n_data.get("total_received", 0.0)
            is_agent = n_data.get("is_agent", False)
            pr = pagerank.get(node_id, 0.0)

            # Rule 1: Fan-out Hub (Primary Mule)
            # Inbound from 1-2 sources, rapidly dispatched to 3+ targets with high flow-through ratio
            flow_through = (sent / received) if received > 0 else 0.0
            
            node_type = "NORMAL_USER"
            risk_score = 0.10
            reasons = []

            if out_deg >= 3 and in_deg >= 1 and 0.70 <= flow_through <= 1.05 and not is_agent:
                node_type = "PRIMARY_MULE"
                risk_score = min(0.98, 0.80 + (out_deg * 0.04))
                reasons.append(f"High fan-out disbursement: 1 in, {out_deg} out (Flow-through {flow_through:.1%})")
                mule_count += 1
            elif is_agent and in_deg >= 3:
                # Multiple accounts cashing out at this agent
                node_type = "CASH_OUT_AGENT"
                risk_score = min(0.92, 0.65 + (in_deg * 0.05))
                reasons.append(f"Convergence cash-out liquidation point ({in_deg} in-degree)")
            elif in_deg >= 1 and out_deg == 1 and not is_agent and sent > 10000.0:
                # Intermediate relay mule
                node_type = "SECONDARY_MULE"
                risk_score = 0.75
                reasons.append("Relay transfer node in rapid disbursement pipeline")
                mule_count += 1
            elif in_deg == 0 and out_deg >= 1 and sent > 20000.0:
                # Source/Victim node
                node_type = "VICTIM"
                risk_score = 0.35
                reasons.append("High-volume transfer origin")

            classified_nodes.append({
                "id": node_id,
                "label": node_id,
                "node_type": node_type,
                "risk_score": round(risk_score, 2),
                "in_degree": in_deg,
                "out_degree": out_deg,
                "total_sent": round(sent, 2),
                "total_received": round(received, 2),
                "pagerank": round(pr, 4),
                "cluster_id": node_to_cluster.get(node_id),
                "is_agent": is_agent,
                "reasons": reasons
            })

        # Format Edges for Visualization
        formatted_edges = []
        for u, v, data in G.edges(data=True):
            formatted_edges.append({
                "id": f"{u}->{v}",
                "source": u,
                "target": v,
                "amount": round(data.get("weight", 0.0), 2),
                "tx_count": data.get("tx_count", 1),
                "is_cash_out": data.get("is_cash_out", False),
                "cluster_id": node_to_cluster.get(u) if node_to_cluster.get(u) == node_to_cluster.get(v) else None
            })

        return {
            "nodes": classified_nodes,
            "edges": formatted_edges,
            "clusters": sorted(clusters_info, key=lambda c: c["size"], reverse=True),
            "summary": {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "mule_nodes_detected": mule_count,
                "clusters_detected": len(clusters_info)
            }
        }

    @classmethod
    def extract_ego_subgraph(cls, G: nx.DiGraph, center_node: str, radius: int = 2) -> Dict[str, Any]:
        """
        Extracts local neighborhood / ego graph around a specific suspect or victim account.
        """
        if not G.has_node(center_node):
            return {
                "nodes": [],
                "edges": [],
                "center_node": center_node,
                "error": f"Node {center_node} not found in transaction network."
            }

        # Get undirected ego graph nodes, then induce directed subgraph
        undirected_G = G.to_undirected(as_view=True)
        ego_nodes = nx.single_source_shortest_path_length(undirected_G, center_node, cutoff=radius).keys()
        subgraph = G.subgraph(ego_nodes).copy()

        analysis = cls.analyze_graph(subgraph)
        analysis["center_node"] = center_node
        return analysis
