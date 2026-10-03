from typing import Generator, Optional, List
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.core.exceptions import AppException
from backend.app.models.user import User, UserRole, UserStatus
from backend.app.models.customer import CustomerProfile
from backend.app.models.agent import AgentProfile

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Validate bearer token and return authenticated User record."""
    if not credentials or not credentials.credentials:
        raise AppException(
            message="Authentication credentials were not provided.",
            code="AUTHENTICATION_REQUIRED",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise AppException(
            message="Invalid, expired or malformed access token.",
            code="INVALID_TOKEN",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    user_id = payload.get("sub")
    if not user_id:
        raise AppException(
            message="Token payload is missing user identity subject.",
            code="INVALID_TOKEN_SUBJECT",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            message="User account associated with this token does not exist.",
            code="USER_NOT_FOUND",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Check token revocation
    if user.token_revoked_at:
        token_ts = payload.get("ts")
        if token_ts is None:
            token_iat = payload.get("iat")
            token_ts = float(token_iat) if token_iat else 0.0

        revoked_ts = user.token_revoked_at.timestamp()
        if token_ts < revoked_ts:
            raise AppException(
                message="Session has been revoked due to security action or logout. Please log in again.",
                code="SESSION_REVOKED",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

    if user.status == UserStatus.SUSPENDED:
        raise AppException(
            message="Your account has been suspended by administration.",
            code="ACCOUNT_SUSPENDED",
            status_code=status.HTTP_403_FORBIDDEN
        )

    return user

def require_role(allowed_roles: List[UserRole]):
    """Enforce Role-Based Access Control (RBAC)."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppException(
                message=f"Access denied. Required role: {[r.value for r in allowed_roles]}, your role: {current_user.role.value}",
                code="FORBIDDEN_INSUFFICIENT_PERMISSIONS",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return current_user
    return role_checker

def require_customer(current_user: User = Depends(require_role([UserRole.CUSTOMER]))) -> User:
    """Enforce customer-only boundary."""
    if not current_user.customer_profile:
        raise AppException(
            message="Customer profile not found for this account.",
            code="PROFILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    return current_user

def require_agent(current_user: User = Depends(require_role([UserRole.AGENT]))) -> User:
    """Enforce merchant/agent-only boundary."""
    if not current_user.agent_profile:
        raise AppException(
            message="Agent profile not found for this account.",
            code="PROFILE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )
    return current_user

def require_risk_analyst(current_user: User = Depends(require_role([UserRole.RISK_ANALYST, UserRole.ADMIN]))) -> User:
    """Enforce Risk Analyst or Admin boundary."""
    return current_user

def require_admin(current_user: User = Depends(require_role([UserRole.ADMIN]))) -> User:
    """Enforce Admin boundary."""
    return current_user
