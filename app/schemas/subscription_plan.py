from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionPlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    price: float = 0
    billing_period: str = "monthly"
    description: Optional[str] = None
    features: Optional[str] = None
    is_active: bool = True


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    price: Optional[float] = None
    billing_period: Optional[str] = None
    description: Optional[str] = None
    features: Optional[str] = None
    is_active: Optional[bool] = None


class SubscriptionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    billing_period: Optional[str] = None
    is_active: bool = True
    features: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
