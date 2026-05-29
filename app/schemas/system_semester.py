from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SystemSemesterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=30)
    display_order: int = Field(1, ge=0, le=999)
    is_active: bool = True


class SystemSemesterCreate(SystemSemesterBase):
    pass


class SystemSemesterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=30)
    display_order: Optional[int] = Field(None, ge=0, le=999)
    is_active: Optional[bool] = None


class SystemSemesterResponse(SystemSemesterBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

