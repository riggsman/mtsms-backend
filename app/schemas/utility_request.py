from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UtilityRequestCreate(BaseModel):
    utility_type: str
    location: Optional[str] = None
    description: str

class UtilityRequestUpdate(BaseModel):
    utility_type: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class UtilityRequestResponse(BaseModel):
    id: int
    institution_id: int
    requested_by: Optional[int] = None
    utility_type: str
    location: Optional[str] = None
    description: str
    status: str
    handled_by: Optional[int] = None
    handled_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True