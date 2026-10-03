from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GraphNodeSchema(BaseModel):
    id: str
    label: str
    node_type: str = Field(..., description="NORMAL_USER, PRIMARY_MULE, SECONDARY_MULE, CASH_OUT_AGENT, VICTIM")
    risk_score: float
    in_degree: int
    out_degree: int
    total_sent: float
    total_received: float
    pagerank: float
    cluster_id: Optional[str] = None
    is_agent: bool = False
    is_frozen: bool = False
    reasons: List[str] = []

class GraphEdgeSchema(BaseModel):
    id: str
    source: str
    target: str
    amount: float
    tx_count: int
    is_cash_out: bool = False
    cluster_id: Optional[str] = None

class MuleClusterSchema(BaseModel):
    cluster_id: str
    size: int
    total_volume: float
    nodes: List[str]

class GraphSummarySchema(BaseModel):
    total_nodes: int
    total_edges: int
    mule_nodes_detected: int
    clusters_detected: int

class GraphTopologyResponse(BaseModel):
    nodes: List[GraphNodeSchema]
    edges: List[GraphEdgeSchema]
    clusters: List[MuleClusterSchema]
    summary: GraphSummarySchema
    center_node: Optional[str] = None
