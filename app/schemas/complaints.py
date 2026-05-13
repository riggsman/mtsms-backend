import json

from pydantic import BaseModel, field_validator
from typing import Optional, List, Any
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
    screenshots: Optional[List[str]] = None
    status: str
    update_note: Optional[str] = None
    resolved_by: Optional[str]
    resolver_role: Optional[str]
    resolved_date: Optional[datetime]
    submission_date: datetime
    created_at: datetime
    updated_at: Optional[datetime]

    @field_validator("screenshots", mode="before")
    @classmethod
    def coerce_screenshots(cls, v: Any) -> Optional[List[str]]:
        """DB column is JSON text; ORM returns a string until explicitly parsed."""
        if v is None or v == "":
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                data = json.loads(v)
                return data if isinstance(data, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return None

    class Config:
        from_attributes = True

class ComplaintUpdate(BaseModel):
    status: Optional[str] = None
    update_note: Optional[str] = None
    resolved_by: Optional[str] = None
    resolver_role: Optional[str] = None
    resolved_date: Optional[datetime] = None
