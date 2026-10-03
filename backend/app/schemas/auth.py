from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from backend.app.models.user import UserRole, UserStatus

class UserRegisterRequest(BaseModel):
    phone: str = Field(..., description="Bangladeshi mobile number, e.g. +8801700000001 or 01700000001")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Account password")
    role: UserRole = Field(default=UserRole.CUSTOMER, description="Role: CUSTOMER, AGENT, or RISK_ANALYST")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full legal or business name")
    
    # Customer specific
    freeze_pin: Optional[str] = Field(None, min_length=4, max_length=6, description="4-6 digit emergency freeze PIN")
    profession: Optional[str] = Field(None, max_length=60)
    location: Optional[str] = Field(None, max_length=100)

    # Agent specific
    agent_code: Optional[str] = Field(None, max_length=20)
    store_name: Optional[str] = Field(None, max_length=120)
    location_cluster: Optional[str] = Field(None, max_length=100)
    is_factory_zone: Optional[bool] = False

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "")
        if cleaned.startswith("01"):
            return "+88" + cleaned
        if not cleaned.startswith("+88"):
            raise ValueError("Phone number must be a valid Bangladeshi number starting with +8801 or 01")
        return cleaned

class UserLoginRequest(BaseModel):
    identifier: str = Field(..., description="Email or phone number")
    password: str = Field(..., min_length=1)

class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    profession: str
    location: str
    wallet_balance: float
    grace_balance: float
    reliability_score: float
    spending_pattern: str

class AgentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_code: str
    store_name: str
    location_cluster: str
    cash_balance: float
    float_balance: float
    is_factory_zone: bool

class UserResponse(BaseModel):
    id: str
    phone: str
    email: str
    role: UserRole
    status: UserStatus
    is_frozen: bool
    created_at: str
    profile: Optional[Union[CustomerProfileResponse, AgentProfileResponse, Dict[str, Any]]] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
