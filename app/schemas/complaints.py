from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ComplaintRequest(BaseModel):
    student_id: str
    complaint_type: str
    caption: str
    contents: str
    is_anonymous: bool = False
    screenshots: Optional[List[str]] = None

class ComplaintResponse(BaseModel):
    id: int
    student_id: str
    complaint_type: str
    caption: str
    contents: str
    is_anonymous: bool
    screenshots: Optional[List[str]]
    status: str
    resolved_by: Optional[str]
    resolver_role: Optional[str]
    resolved_date: Optional[datetime]
    submission_date: datetime
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    resolved_by: Optional[str] = None
    resolver_role: Optional[str] = None
    resolved_date: Optional[datetime] = None
