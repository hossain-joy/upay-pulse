from datetime import timedelta, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import (
    verify_password,
    get_password_hash,
    get_freeze_pin_hash,
    create_access_token
)
from backend.app.core.config import settings
from backend.app.core.exceptions import AppException
from backend.app.models.user import User, UserRole, UserStatus
from backend.app.models.customer import CustomerProfile
from backend.app.models.agent import AgentProfile
from backend.app.models.audit import AuditLog
from backend.app.models.base import utc_now
from backend.app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    CustomerProfileResponse,
    AgentProfileResponse
)
from backend.app.api.deps import (
    get_current_user,
    require_customer,
    require_agent,
    require_risk_analyst,
    require_admin
)

router = APIRouter()

def build_user_response(user: User) -> UserResponse:
    profile_data = None
    if user.role == UserRole.CUSTOMER and user.customer_profile:
        p = user.customer_profile
        profile_data = CustomerProfileResponse(
            id=p.id,
            full_name=p.full_name,
            profession=p.profession,
            location=p.location,
            wallet_balance=float(p.wallet_balance),
            grace_balance=float(p.grace_balance),
            reliability_score=float(p.reliability_score),
            spending_pattern=p.spending_pattern
        )
    elif user.role == UserRole.AGENT and user.agent_profile:
        p = user.agent_profile
        profile_data = AgentProfileResponse(
            id=p.id,
            agent_code=p.agent_code,
            store_name=p.store_name,
            location_cluster=p.location_cluster,
            cash_balance=float(p.cash_balance),
            float_balance=float(p.float_balance),
            is_factory_zone=p.is_factory_zone
        )

    return UserResponse(
        id=user.id,
        phone=user.phone,
        email=user.email,
        role=user.role,
        status=user.status,
        is_frozen=user.is_frozen,
        created_at=user.created_at.isoformat() if user.created_at else "",
        profile=profile_data
    )

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new customer or agent account."""
    # Check phone uniqueness
    existing_phone = db.query(User).filter(User.phone == req.phone).first()
    if existing_phone:
        raise AppException(
            message="An account with this phone number already exists.",
            code="PHONE_ALREADY_EXISTS",
            status_code=status.HTTP_409_CONFLICT
        )

    # Check email uniqueness
    existing_email = db.query(User).filter(User.email == req.email).first()
    if existing_email:
        raise AppException(
            message="An account with this email address already exists.",
            code="EMAIL_ALREADY_EXISTS",
            status_code=status.HTTP_409_CONFLICT
        )

    # Hash credentials
    hashed_pwd = get_password_hash(req.password)
    freeze_hash = get_freeze_pin_hash(req.freeze_pin) if req.freeze_pin else None

    # Default freeze PIN for customers if omitted: "1234"
    if req.role == UserRole.CUSTOMER and not freeze_hash:
        freeze_hash = get_freeze_pin_hash("1234")

    new_user = User(
        phone=req.phone,
        email=req.email,
        hashed_password=hashed_pwd,
        freeze_pin_hash=freeze_hash,
        role=req.role,
        status=UserStatus.ACTIVE
    )
    db.add(new_user)
    db.flush()

    # Create associated profile
    if req.role == UserRole.CUSTOMER:
        profile = CustomerProfile(
            user_id=new_user.id,
            full_name=req.full_name,
            profession=req.profession or "General",
            location=req.location or "Dhaka",
            wallet_balance=500.00,  # Seed initial demo balance
            grace_balance=0.00,
            reliability_score=0.85
        )
        db.add(profile)
    elif req.role == UserRole.AGENT:
        agent_code = req.agent_code or f"AGT-{new_user.phone[-4:]}"
        profile = AgentProfile(
            user_id=new_user.id,
            agent_code=agent_code,
            store_name=req.store_name or f"{req.full_name} Store",
            location_cluster=req.location_cluster or "Dhaka Central",
            cash_balance=50000.00,
            float_balance=100000.00,
            is_factory_zone=req.is_factory_zone or False
        )
        db.add(profile)

    # Audit log
    db.add(AuditLog(
        actor_id=new_user.id,
        actor_role=new_user.role.value,
        action="USER_REGISTRATION",
        resource="USERS",
        resource_id=new_user.id,
        details=f'{{"email": "{new_user.email}", "role": "{new_user.role.value}"}}'
    ))

    db.commit()
    db.refresh(new_user)

    # Issue JWT token
    token = create_access_token(data={"sub": new_user.id, "role": new_user.role.value})
    user_resp = build_user_response(new_user)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_resp
    )

@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate via email or phone and return access token."""
    identifier = req.identifier.strip()
    user = db.query(User).filter(
        (User.email == identifier) | (User.phone == identifier)
    ).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise AppException(
            message="Invalid credentials. Please verify your phone/email and password.",
            code="INVALID_CREDENTIALS",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    if user.status == UserStatus.SUSPENDED:
        raise AppException(
            message="Your account has been suspended.",
            code="ACCOUNT_SUSPENDED",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # A successful login re-validates the user's session. If the previous
    # session was revoked (e.g., by a Master Freeze), the freshly issued token
    # must be accepted — otherwise they could not log back in to complete the
    # unfreeze flow.
    user.token_revoked_at = None

    # Audit login
    db.add(AuditLog(
        actor_id=user.id,
        actor_role=user.role.value,
        action="USER_LOGIN",
        resource="AUTH",
        resource_id=user.id
    ))
    db.commit()

    token = create_access_token(data={"sub": user.id, "role": user.role.value})
    user_resp = build_user_response(user)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_resp
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get active authenticated user details and profile."""
    return build_user_response(current_user)

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke active tokens for this user."""
    current_user.token_revoked_at = utc_now()
    db.add(AuditLog(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action="USER_LOGOUT",
        resource="AUTH",
        resource_id=current_user.id
    ))
    db.commit()
    return {"success": True, "message": "Logged out successfully. All sessions revoked."}

# RBAC Test Endpoints for Verification
@router.get("/rbac-test/customer-only")
def test_customer_route(user: User = Depends(require_customer)):
    return {"message": "Access granted to customer", "user_id": user.id, "balance": float(user.customer_profile.wallet_balance)}

@router.get("/rbac-test/agent-only")
def test_agent_route(user: User = Depends(require_agent)):
    return {"message": "Access granted to agent", "agent_code": user.agent_profile.agent_code}

@router.get("/rbac-test/admin-only")
def test_admin_route(user: User = Depends(require_admin)):
    return {"message": "Access granted to administrator", "user_id": user.id}
