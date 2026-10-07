"""
upay Pulse — Mule Network Evolution endpoints.

GET /api/v1/graph/evolution/datasets?bucket_days=7
    Returns the chronological list of time-windowed datasets derived from
    the existing Transaction.created_at timestamps. bucket_days ∈ {1,3,7,14,30}.

GET /api/v1/graph/evolution/{dataset_id}?bucket_days=7&top_n=100
    Returns the full graph snapshot (re-using Phase-2 MuleGraphDetector)
    scoped to that dataset's [start, end) window.

GET /api/v1/graph/evolution/{dataset_id}/changes?from={prev_id}&bucket_days=7
    Returns the diff between two consecutive snapshots: new/removed nodes,
    new/removed edges, risk_score escalations/de-escalations, and
    cluster-membership changes.

GET /api/v1/graph/evolution/{dataset_id}/emerging?from={prev_id}&bucket_days=7
    Returns accounts/clusters whose mule risk is newly classified or
    escalated (>=0.70 from <=0.40) compared to the previous snapshot.

All endpoints require ADMIN or RISK_ANALYST role.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import require_risk_analyst
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.graph_evolution import (
    EvolutionDatasetList,
    EvolutionSnapshotResponse,
    EvolutionDiffResponse,
    EmergingMulesResponse,
)
from backend.app.services.evolution_service import (
    EvolutionService,
    DEFAULT_BUCKET_DAYS,
    DEFAULT_TOP_N,
)


router = APIRouter()


@router.get(
    "/evolution/datasets",
    response_model=EvolutionDatasetList,
    tags=["SecurityAI: Mule Network Evolution"],
)
def list_evolution_datasets(
    bucket_days: Optional[int] = Query(
        DEFAULT_BUCKET_DAYS,
        description="Window size in days; one of 1, 3, 7, 14, 30.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_risk_analyst),
):
    """List chronological datasets available for evolution visualisation."""
    return EvolutionService.list_datasets(db, bucket_days=bucket_days)


@router.get(
    "/evolution/{dataset_id}",
    response_model=EvolutionSnapshotResponse,
    tags=["SecurityAI: Mule Network Evolution"],
)
def get_evolution_snapshot(
    dataset_id: str,
    bucket_days: Optional[int] = Query(DEFAULT_BUCKET_DAYS),
    top_n: int = Query(
        DEFAULT_TOP_N,
        ge=1,
        le=2000,
        description="Cap on nodes returned (sorted by risk_score desc).",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_risk_analyst),
):
    """Compute and return a single dataset's graph snapshot."""
    return EvolutionService.get_snapshot(
        db=db,
        dataset_id=dataset_id,
        bucket_days=bucket_days,
        top_n=top_n,
    )


@router.get(
    "/evolution/{dataset_id}/changes",
    response_model=EvolutionDiffResponse,
    tags=["SecurityAI: Mule Network Evolution"],
)
def get_evolution_changes(
    dataset_id: str,
    from_dataset_id: str = Query(..., alias="from", description="Previous dataset id."),
    bucket_days: Optional[int] = Query(DEFAULT_BUCKET_DAYS),
    top_n: int = Query(DEFAULT_TOP_N, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_risk_analyst),
):
    """Diff two consecutive datasets: node/edge/risk/cluster deltas."""
    return EvolutionService.get_diff(
        db=db,
        dataset_id=dataset_id,
        from_dataset_id=from_dataset_id,
        bucket_days=bucket_days,
        top_n=top_n,
    )


@router.get(
    "/evolution/{dataset_id}/emerging",
    response_model=EmergingMulesResponse,
    tags=["SecurityAI: Mule Network Evolution"],
)
def get_evolution_emerging(
    dataset_id: str,
    from_dataset_id: str = Query(..., alias="from", description="Previous dataset id."),
    bucket_days: Optional[int] = Query(DEFAULT_BUCKET_DAYS),
    top_n: int = Query(DEFAULT_TOP_N, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_risk_analyst),
):
    """Identify newly classified or risk-escalated mule accounts."""
    return EvolutionService.get_emerging(
        db=db,
        dataset_id=dataset_id,
        from_dataset_id=from_dataset_id,
        bucket_days=bucket_days,
        top_n=top_n,
    )