from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class SubscriptionServiceRequest(BaseModel):
    """Request model for creating/updating subscription services.

    Field names are aligned with the JSON sent by the Service Management UI.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    price: Decimal = Field(..., ge=0, description="Service price")
    currency: str = Field(default="USD", max_length=10, description="Currency code")
    billing_period: str = Field(
        ..., description="Billing period: monthly, yearly, or one-time"
    )
    is_active: bool = Field(default=True, description="Whether the service is active")
    # These match the checkbox field names in the React UI
    freemium_enabled: Optional[bool] = Field(
        default=False,
        description="Whether this service is available on the freemium plan",
    )
    premium_enabled: Optional[bool] = Field(
        default=False,
        description="Whether this service is available on the premium plan",
    )
    max_free_download: Optional[int] = Field(
        default=None,
        ge=0,
        description="Free usage count before payment is required",
    )
    features: Optional[Dict[str, Any]] = Field(
        None, description="Service features as JSON object"
    )


class SubscriptionServiceResponse(BaseModel):
    """Response model for subscription services.

    Field names match what the frontend expects.
    """

    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    currency: str
    billing_period: str
    is_active: bool
    freemium_enabled: bool
    premium_enabled: bool
    max_free_download: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
