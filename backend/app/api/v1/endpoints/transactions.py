from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.exceptions import AppException
from backend.app.models.user import User
from backend.app.models.transaction import Transaction, TransactionType
from backend.app.schemas.transaction import (
    SendMoneyRequest,
    CashOutRequest,
    CashInRequest,
    TransactionResponse,
    TransactionHistoryResponse
)
from backend.app.api.deps import (
    get_current_user,
    require_customer,
    require_agent
)
from backend.app.services.transaction_service import (
    TransactionService,
    format_transaction_response
)

router = APIRouter()

@router.post("/send", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def send_money(
    req: SendMoneyRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    """Customer send money transfer with automated Grace overdraft fallback."""
    return TransactionService.send_money(db=db, sender=current_user, req=req)

@router.post("/cash-out", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def cash_out(
    req: CashOutRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db)
):
    """Customer cash withdrawal at an agent counter."""
    return TransactionService.cash_out(db=db, customer=current_user, req=req)

@router.post("/cash-in", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def cash_in(
    req: CashInRequest,
    current_user: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """Agent deposit to customer wallet with automated Grace loan recovery."""
    return TransactionService.cash_in(db=db, agent=current_user, req=req)

@router.get("/history", response_model=TransactionHistoryResponse)
def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tx_type: Optional[TransactionType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve filtered, paginated transaction ledger based on user role."""
    data = TransactionService.get_history(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        tx_type=tx_type
    )
    return TransactionHistoryResponse(**data)

@router.get("/{txn_id}", response_model=TransactionResponse)
def get_transaction(
    txn_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single transaction detail by ID or reference."""
    txn = db.query(Transaction).filter(
        (Transaction.id == txn_id) | (Transaction.transaction_reference == txn_id)
    ).first()

    if not txn:
        raise AppException("Transaction record not found.", code="NOT_FOUND", status_code=404)

    # Authorization check
    if current_user.role == "CUSTOMER" and current_user.id not in [txn.sender_id, txn.receiver_id]:
        raise AppException("Access denied to this transaction record.", code="FORBIDDEN", status_code=403)
    if current_user.role == "AGENT" and current_user.id != txn.agent_id:
        raise AppException("Access denied to this agent transaction.", code="FORBIDDEN", status_code=403)

    return format_transaction_response(txn)
