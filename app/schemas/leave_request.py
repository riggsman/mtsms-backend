from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None

class LeaveRequestUpdate(BaseModel):
    leave_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[str] = None

class LeaveRequestResponse(BaseModel):
    id: int
    institution_id: int
    staff_id: int
    leave_type: str
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True