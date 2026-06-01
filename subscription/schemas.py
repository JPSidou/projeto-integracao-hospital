from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from models import PlanName, SubscriptionStatus, PaymentStatus


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    plan: Optional[str] = None
    subscription_status: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class PlanCreate(BaseModel):
    name: PlanName
    description: Optional[str] = None
    monthly_price: float = Field(..., gt=0)


class PlanResponse(BaseModel):
    id: int
    name: PlanName
    description: Optional[str]
    monthly_price: float

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    user_id: int
    plan_id: int
    expires_at: Optional[datetime] = None


class SubscriptionUpdate(BaseModel):
    status: SubscriptionStatus
    expires_at: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    status: SubscriptionStatus
    started_at: datetime
    expires_at: Optional[datetime]
    plan: Optional[PlanResponse] = None

    class Config:
        from_attributes = True


class PaymentCreate(BaseModel):
    subscription_id: int
    amount: float = Field(..., gt=0)
    status: PaymentStatus = PaymentStatus.PENDING


class PaymentResponse(BaseModel):
    id: int
    subscription_id: int
    amount: float
    status: PaymentStatus
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    detail: str
