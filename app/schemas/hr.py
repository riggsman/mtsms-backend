from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal

class StaffDocumentBase(BaseModel):
    document_type: str
    file_name: str
    file_path: str
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None

class StaffDocumentCreate(StaffDocumentBase):
    staff_id: int

class StaffDocumentResponse(StaffDocumentBase):
    id: int
    staff_id: int
    institution_id: int
    upload_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class StaffAttendanceBase(BaseModel):
    staff_id: int
    date: datetime
    clock_in: Optional[datetime] = None
    clock_out: Optional[datetime] = None
    status: str = "present"
    notes: Optional[str] = None

class StaffAttendanceCreate(StaffAttendanceBase):
    pass

class StaffAttendanceResponse(StaffAttendanceBase):
    id: int
    institution_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class LeaveRequestResponse(BaseModel):
    id: int
    staff_id: int
    leave_type: str
    start_date: datetime
    end_date: datetime
    reason: Optional[str]
    status: str
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
