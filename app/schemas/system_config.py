from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SystemConfigBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None

class SystemConfigCreate(SystemConfigBase):
    pass

class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None

class SystemConfigResponse(SystemConfigBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DatabaseModeResponse(BaseModel):
    mode: str  # 'shared' or 'multi_tenant'
    description: str

class DatabaseModeUpdate(BaseModel):
    mode: str  # 'shared' or 'multi_tenant'
