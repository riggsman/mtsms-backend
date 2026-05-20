from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, Literal
from datetime import datetime, timezone, timedelta

BILLING_CYCLE_DAYS = 31


class TenantSuspendRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=4000)


class TenantResponse(BaseModel):
    id: int
    name: str
    region: Optional[str] = None
    city : Optional[str] = None
    neighbourhood: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    category: str  # HI or SI
    domain: Optional[str] = None
    database_url: Optional[str] = None
    is_active: bool = True
    services_activated: bool = False
    services_activated_at: Optional[datetime] = None
    services_activated_by: Optional[int] = None
    suspension_reason: Optional[str] = None
    suspended_at: Optional[datetime] = None
    logo_url: Optional[str] = None  # URL to tenant logo
    branches_enabled: bool = False  # Multi-campus / branch mode
    fee_amount: Optional[float] = None  # Total fee amount for the tenant
    fee_deadline: Optional[datetime] = None  # Final payment deadline / subscription expiry
    subscription_plan: Optional[str] = None
    subscription_started_at: Optional[datetime] = None
    billing_type: Optional[str] = None
    payment_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    admin_username: Optional[str] = None
    phone: Optional[str] = Field(
        default=None,
        description="Institution contact phone for display (fallback from admin user)",
    )

    @computed_field
    @property
    def subscription_is_paid(self) -> bool:
        if self.fee_amount is None:
            return False
        try:
            return float(self.fee_amount) > 0
        except (TypeError, ValueError):
            return False

    @computed_field
    @property
    def subscription_days_remaining(self) -> Optional[int]:
        if self.fee_deadline is None:
            return None
        deadline = self.fee_deadline
        if hasattr(deadline, "date"):
            end_d = deadline.date()
        else:
            end_d = deadline
        today = datetime.now(timezone.utc).date()
        return (end_d - today).days

    @computed_field
    @property
    def next_subscription_date(self) -> Optional[datetime]:
        if not self.subscription_plan or self.subscription_plan.lower() == 'freemium':
            return None
        if 'premium' not in (self.subscription_plan or '').lower():
            return None
        payment = self.payment_date or self.subscription_started_at
        if not payment:
            return None
        return payment + timedelta(days=BILLING_CYCLE_DAYS)

    class Config:
        from_attributes = True


class TenantRequest(BaseModel):
    name: str
    region: str = Field(..., min_length=1, max_length=70)
    city: str = Field(..., min_length=1, max_length=70)
    neighbourhood: str = Field(..., min_length=1, max_length=70)
    email: str = Field(..., min_length=1, max_length=70, description="Institution contact email")
    telephone: str = Field(..., min_length=1, max_length=70, description="Institution contact telephone")
    category: Literal["HI", "SI"] = Field(..., description="Tenant category: HI (Higher Institution) or SI (Secondary Institution)")
    domain: Optional[str] = None
    database_name: Optional[str] = None
    is_active: Optional[bool] = True
    branches_enabled: Optional[bool] = None  # Create/use branches for this tenant
    # Optional: create the first branch when branches_enabled is enabled during tenant setup.
    initial_branch_name: Optional[str] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    must_change_password: Optional[bool] = False
    subscription_plan: Optional[str] = Field(None, description="Subscription tier label")
    billing_type: Optional[str] = Field(None, description="Billing period: monthly, quarterly, annually")
    subscription_started_at: Optional[str] = Field(
        None, description="Subscription period start (YYYY-MM-DD or ISO datetime)"
    )

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v.upper() not in ['HI', 'SI']:
            raise ValueError('Category must be either "HI" or "SI"')
        return v.upper()

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = Field(None, max_length=70)
    city: Optional[str] = Field(None, max_length=70)
    neighbourhood: Optional[str] = Field(None, max_length=70)
    email: Optional[str] = Field(None, max_length=70, description="Institution contact email")
    telephone: Optional[str] = Field(None, max_length=70, description="Institution contact telephone")
    category: Optional[Literal["HI", "SI"]] = Field(None, description="Tenant category: HI (Higher Institution) or SI (Secondary Institution)")
    domain: Optional[str] = None
    is_active: Optional[bool] = None
    branches_enabled: Optional[bool] = None  # Update branches mode for this tenant
    fee_amount: Optional[float] = Field(None, description="Total fee amount for the tenant")
    fee_deadline: Optional[str] = Field(None, description="Final payment deadline (ISO format)")
    subscription_plan: Optional[str] = Field(None, description="Subscription tier label")
    subscription_started_at: Optional[str] = Field(
        None, description="Subscription period start (YYYY-MM-DD or ISO datetime)"
    )
    billing_type: Optional[str] = Field(None, description="Billing period: monthly, quarterly, yearly")
    payment_date: Optional[str] = Field(None, description="Payment date for premium users (ISO datetime)")
    initial_branch_name: Optional[str] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    must_change_password: Optional[bool] = None

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in ['HI', 'SI']:
            raise ValueError('Category must be either "HI" or "SI"')
        return v.upper() if v else None