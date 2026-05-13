from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, Literal
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta


class TenantSuspendRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=4000)


class TenantResponse(BaseModel):
    id: int
    name: str
    category: str  # HI or SI
    domain: Optional[str] = None
    database_url: Optional[str] = None
    is_active: bool = True
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
    email: Optional[str] = Field(
        default=None,
        description="Institution contact email for display (e.g. receipts)",
    )
    phone: Optional[str] = Field(
        default=None,
        description="Institution contact phone for display (e.g. receipts)",
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
        # Only calculate for paid plans (non-freemium)
        if not self.subscription_plan or self.subscription_plan.lower() == 'freemium':
            return None
        start = self.subscription_started_at
        billing = self.billing_type
        if not start or not billing:
            return None
        if billing == "monthly":
            return start + relativedelta(months=1)
        elif billing == "quarterly":
            return start + relativedelta(months=3)
        elif billing == "yearly" or billing == "annually":
            return start + relativedelta(years=1)
        return None

    class Config:
        from_attributes = True


class TenantRequest(BaseModel):
    name: str
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