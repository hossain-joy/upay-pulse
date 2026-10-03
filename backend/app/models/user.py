import enum
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    AGENT = "AGENT"
    RISK_ANALYST = "RISK_ANALYST"
    ADMIN = "ADMIN"

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    SUSPENDED = "SUSPENDED"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.CUSTOMER, nullable=False, index=True)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False, index=True)
    
    # Security & Freeze State
    is_frozen = Column(Boolean, default=False, nullable=False, index=True)
    freeze_pin_hash = Column(String(255), nullable=True)
    failed_pin_attempts = Column(Integer, default=0, nullable=False)
    token_revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    agent_profile = relationship("AgentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    freeze_actions = relationship("FreezeAction", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User phone={self.phone} role={self.role} status={self.status}>"
