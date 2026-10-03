from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import require_admin
from backend.app.models.user import User
from backend.app.schemas.graph import GraphTopologyResponse, MuleClusterSchema
from backend.app.services.graph_intelligence_service import GraphIntelligenceService

router = APIRouter()

@router.get("/topology", response_model=GraphTopologyResponse)
def get_graph_topology(
    cluster_id: Optional[str] = None,
    min_amount: float = Query(0.0, ge=0.0),
    limit: int = Query(1000, ge=10, le=10000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Retrieve full or cluster-filtered transaction graph topology for Risk Console visualizer.
    """
    return GraphIntelligenceService.get_full_graph(
        db=db,
        cluster_id=cluster_id,
        min_amount=min_amount,
        limit=limit
    )

@router.get("/ego/{account_identifier}", response_model=GraphTopologyResponse)
def get_ego_graph(
    account_identifier: str,
    radius: int = Query(2, ge=1, le=3),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Extract 1-hop or 2-hop local ego network around a specific suspect or victim account.
    """
    return GraphIntelligenceService.get_ego_graph(
        db=db,
        account_identifier=account_identifier,
        radius=radius
    )

@router.get("/mule-rings", response_model=List[MuleClusterSchema])
def get_mule_rings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    List all detected money-mule syndicate clusters and their membership.
    """
    return GraphIntelligenceService.get_mule_clusters(db=db)

@router.post("/sync")
def sync_graph_tables(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Trigger batch graph analysis and persist mule nodes and edges into DB tables.
    """
    return GraphIntelligenceService.sync_graph_to_database(db=db)
