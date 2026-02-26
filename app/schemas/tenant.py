from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TenantResponse(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None
    database_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    admin_username: Optional[str] = None
   
    class Config:
        from_attributes = True

class TenantRequest(BaseModel):
    name: str
    domain: Optional[str] = None
    database_name: Optional[str] = None
    is_active: Optional[bool] = True
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    must_change_password: Optional[bool] = False

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None
    admin_username: Optional[str] = None
    admin_password: Optional[str] = None
    must_change_password: Optional[bool] = None