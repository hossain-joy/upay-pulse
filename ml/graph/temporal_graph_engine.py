"""
upay Pulse — Fast Temporal Graph Intelligence Engine (Workstream 7)
Dynamic sliding-window graph tracker with O(1) incremental degree updates.
Extracts 4 structural topology features strictly on historical edges (< t):
- graph_in_degree_fan_ratio
- graph_pagerank_score
- graph_mule_community_risk
- graph_is_cycle_participant
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque
import pandas as pd
import numpy as np

GRAPH_FEATURE_COLUMNS = [
    "graph_in_degree_fan_ratio",
    "graph_pagerank_score",
    "graph_mule_community_risk",
    "graph_is_cycle_participant"
]

class FastTemporalGraphEngine:
    def __init__(self, window_days: int = 7):
        self.window = timedelta(days=window_days)
        # Sliding edge queue: deque of (timestamp, source, target, amount)
        self.edge_queue: deque = deque()
        # Dynamic adjacency
        self.in_neighbors: Dict[str, Set[str]] = defaultdict(set)
        self.out_neighbors: Dict[str, Set[str]] = defaultdict(set)
        self.edge_counts: Dict[str, int] = defaultdict(int)
        self.total_edges: int = 0

    def _expire_old_edges(self, current_time: datetime):
        cutoff = current_time - self.window
        while self.edge_queue and self.edge_queue[0][0] < cutoff:
            _, u, v, _ = self.edge_queue.popleft()
            pair = f"{u}->{v}"
            self.edge_counts[pair] -= 1
            if self.edge_counts[pair] == 0:
                self.out_neighbors[u].discard(v)
                self.in_neighbors[v].discard(u)
                del self.edge_counts[pair]
            self.total_edges -= 1

    def add_edge(self, timestamp: datetime, source: str, target: str, amount: float):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        self.edge_queue.append((timestamp, source, target, amount))
        pair = f"{source}->{target}"
        self.edge_counts[pair] += 1
        self.out_neighbors[source].add(target)
        self.in_neighbors[target].add(source)
        self.total_edges += 1

    def extract_graph_features(
        self,
        timestamp: datetime,
        source: Optional[str],
        target: Optional[str]
    ) -> Dict[str, float]:
        """
        Extract features strictly prior to `timestamp`.
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        self._expire_old_edges(timestamp)

        if not target or self.total_edges == 0:
            return {
                "graph_in_degree_fan_ratio": 1.0,
                "graph_pagerank_score": 0.001,
                "graph_mule_community_risk": 0.0,
                "graph_is_cycle_participant": 0.0
            }

        # 1. Receiver In-degree vs Out-degree Fan Ratio
        in_deg = len(self.in_neighbors.get(target, set()))
        out_deg = len(self.out_neighbors.get(target, set()))
        fan_ratio = float(in_deg) / max(out_deg, 1.0)

        # 2. Local Centrality Proxy (approximate PageRank based on incoming connectivity)
        pr_score = float(round(min(0.25, in_deg / max(self.total_edges * 0.1, 10.0)), 4))

        # 3. Mule Community Risk: proportion of neighbors acting as fan-out hubs
        all_neighbors = self.in_neighbors.get(target, set()).union(self.out_neighbors.get(target, set()))
        if all_neighbors:
            hub_count = sum(1 for n in all_neighbors if len(self.out_neighbors.get(n, set())) >= 3)
            comm_risk = float(round(hub_count / len(all_neighbors), 3))
        else:
            comm_risk = 0.0

        # 4. Cycle Participation: Does target reach source within 4 hops?
        is_cycle = 0.0
        if source and target:
            visited = {target}
            queue = deque([(target, 1)])
            while queue:
                curr, depth = queue.popleft()
                if source in self.out_neighbors.get(curr, set()):
                    is_cycle = 1.0
                    break
                if depth < 4:
                    for nxt in self.out_neighbors.get(curr, set()):
                        if nxt not in visited:
                            visited.add(nxt)
                            queue.append((nxt, depth + 1))

        return {
            "graph_in_degree_fan_ratio": float(round(fan_ratio, 3)),
            "graph_pagerank_score": pr_score,
            "graph_mule_community_risk": comm_risk,
            "graph_is_cycle_participant": float(is_cycle)
        }


def enrich_dataset_with_temporal_graph(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches transaction dataframe with temporal graph features strictly prior to event.
    Executes in O(N) using sliding window edge queue.
    """
    df = df.copy()
    if "created_at_dt" not in df.columns:
        df["created_at_dt"] = pd.to_datetime(df["created_at"])
    df = df.sort_values("created_at_dt").reset_index(drop=True)

    engine = FastTemporalGraphEngine(window_days=7)
    n = len(df)

    fan_ratios = np.zeros(n, dtype=float)
    pageranks = np.zeros(n, dtype=float)
    comm_risks = np.zeros(n, dtype=float)
    cycles = np.zeros(n, dtype=float)

    for i in range(n):
        row = df.iloc[i]
        t = row["created_at_dt"]
        s = str(row["sender_id"]) if pd.notna(row["sender_id"]) else None
        r = str(row["receiver_id"]) if pd.notna(row["receiver_id"]) else None
        amt = float(row["amount"])

        # Extract features strictly before adding current edge
        feats = engine.extract_graph_features(timestamp=t, source=s, target=r)
        fan_ratios[i] = feats["graph_in_degree_fan_ratio"]
        pageranks[i] = feats["graph_pagerank_score"]
        comm_risks[i] = feats["graph_mule_community_risk"]
        cycles[i] = feats["graph_is_cycle_participant"]

        # Append edge for future transactions
        if s and r:
            engine.add_edge(timestamp=t, source=s, target=r, amount=amt)

    df["graph_in_degree_fan_ratio"] = fan_ratios
    df["graph_pagerank_score"] = pageranks
    df["graph_mule_community_risk"] = comm_risks
    df["graph_is_cycle_participant"] = cycles

    return df
