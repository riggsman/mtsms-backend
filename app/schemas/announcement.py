from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AnnouncementCreate(BaseModel):
    title: str
    content: str
    target_audience: str = Field(default="all", pattern="^(students|staff|all)$")

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    target_audience: Optional[str] = Field(None, pattern="^(students|staff|all)$")

class AnnouncementResponse(BaseModel):
    id: int
    institution_id: int
    title: str
    content: str
    target_audience: str
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
