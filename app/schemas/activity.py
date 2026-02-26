from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ActivityRequest(BaseModel):
    institution_id: int
    action: str
    entity_type: str  # e.g., "user", "course", "schedule", "student", "student_record"
    entity_id: Optional[int] = None
    performed_by: str
    performer_role: str
    performer_id: Optional[int] = None
    content: Optional[str] = None

class ActivityResponse(BaseModel):
    id: int
    institution_id: int
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    performed_by: str
    performer_role: str
    performer_id: Optional[int] = None
    content: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
