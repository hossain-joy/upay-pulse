from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.schemas.graph import (
    GraphNodeSchema,
    GraphEdgeSchema,
    MuleClusterSchema,
    GraphSummarySchema,
)


# ---------------------------------------------------------------------------
# Dataset list
# ---------------------------------------------------------------------------
class EvolutionDataset(BaseModel):
    id: str = Field(..., description="Stable id such as 'W07'.")
    start: str = Field(..., description="ISO timestamp of window start.")
    end: str = Field(..., description="ISO timestamp of window end (exclusive).")
    tx_count: int = Field(..., description="Number of COMPLETED transactions in this window.")
    label: str = Field(..., description="Human-friendly label such as 'Jul 9 – Jul 15'.")


class EvolutionDatasetList(BaseModel):
    bucket_days: Optional[int] = Field(None, description="Window size in days; null = full window.")
    window_start: Optional[str] = Field(None, description="ISO timestamp of dataset range start.")
    window_end: Optional[str] = Field(None, description="ISO timestamp of dataset range end.")
    datasets: List[EvolutionDataset] = []


# ---------------------------------------------------------------------------
# Snapshot (one period)
# ---------------------------------------------------------------------------
class EvolutionSnapshotResponse(BaseModel):
    dataset_id: str
    start: str
    end: str
    label: str
    tx_count: int
    bucket_days: Optional[int] = None
    nodes: List[GraphNodeSchema] = []
    edges: List[GraphEdgeSchema] = []
    clusters: List[MuleClusterSchema] = []
    summary: GraphSummarySchema


# ---------------------------------------------------------------------------
# Diff (two snapshots compared)
# ---------------------------------------------------------------------------
class RiskDeltaEntry(BaseModel):
    id: str
    label: str
    previous: float = Field(..., alias="from", description="Previous risk_score.")
    current: float = Field(..., alias="to", description="Current risk_score.")
    delta: float

    class Config:
        populate_by_name = True


class ClusterChangeEntry(BaseModel):
    cluster_id: str
    overlap: float
    added: List[str] = []
    removed: List[str] = []


class EvolutionDiffStats(BaseModel):
    new_nodes_count: int
    removed_nodes_count: int
    new_edges_count: int
    removed_edges_count: int
    risk_up_count: int
    risk_down_count: int
    cluster_changes_count: int


class EvolutionDiffResponse(BaseModel):
    from_dataset: str = Field(..., alias="from", description="Previous dataset id.")
    to_dataset: str = Field(..., alias="to", description="Current dataset id.")
    bucket_days: Optional[int] = None
    new_nodes: List[GraphNodeSchema] = []
    removed_nodes: List[GraphNodeSchema] = []
    new_edges: List[GraphEdgeSchema] = []
    removed_edges: List[GraphEdgeSchema] = []
    risk_up: List[RiskDeltaEntry] = []
    risk_down: List[RiskDeltaEntry] = []
    cluster_changes: List[ClusterChangeEntry] = []
    stats: EvolutionDiffStats

    class Config:
        populate_by_name = True


# ---------------------------------------------------------------------------
# Emerging mules
# ---------------------------------------------------------------------------
class EmergingMuleEntry(BaseModel):
    id: str
    label: str
    node_type: str
    risk_score: float
    emergence: str = Field(..., description="'newly_classified' or 'risk_escalated'.")
    previous_risk: Optional[float] = None
    cluster_id: Optional[str] = None


class EmergingMulesResponse(BaseModel):
    from_dataset: str = Field(..., alias="from")
    to_dataset: str = Field(..., alias="to")
    count: int
    mules: List[EmergingMuleEntry] = []

    class Config:
        populate_by_name = True