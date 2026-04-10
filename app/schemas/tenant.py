from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime

class TenantResponse(BaseModel):
    id: int
    name: str
    category: str  # HI or SI
    domain: Optional[str] = None
    database_url: Optional[str] = None
    is_active: bool = True
    logo_url: Optional[str] = None  # URL to tenant logo
    branches_enabled: bool = False  # Multi-campus / branch mode
    fee_amount: Optional[float] = None  # Total fee amount for the tenant
    fee_deadline: Optional[datetime] = None  # Final payment deadline
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    admin_username: Optional[str] = None
   
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