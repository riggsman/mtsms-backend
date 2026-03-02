from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class SubscriptionServiceRequest(BaseModel):
    """Request model for creating/updating subscription services"""

    name: str = Field(..., min_length=1, max_length=200, description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    price: Decimal = Field(..., ge=0, description="Service price")
    currency: str = Field(default="USD", max_length=10, description="Currency code")
    billing_period: str = Field(
        ..., description="Billing period: monthly, yearly, or one-time"
    )
    is_active: bool = Field(default=True, description="Whether the service is active")
    features: Optional[Dict[str, Any]] = Field(
        None, description="Service features as JSON object"
    )


class SubscriptionServiceResponse(BaseModel):
    """Response model for subscription services"""

    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    currency: str
    billing_period: str
    is_active: bool
    features: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
