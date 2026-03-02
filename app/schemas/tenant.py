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
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    must_change_password: Optional[bool] = None

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in ['HI', 'SI']:
            raise ValueError('Category must be either "HI" or "SI"')
        return v.upper() if v else None