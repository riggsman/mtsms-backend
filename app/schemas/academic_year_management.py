from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class AcademicYearCreateRequest(BaseModel):
    name: str = Field(..., min_length=4, max_length=100)
    start_date: str = Field(..., min_length=4, max_length=50)
    end_date: str = Field(..., min_length=4, max_length=50)
    is_current: bool = False


class AcademicYearIncrementRequest(BaseModel):
    set_current: bool = True
    copy_date_span: bool = True


class AcademicYearResponse(BaseModel):
    id: int
    institution_id: int
    name: str
    start_date: str
    end_date: str
    is_current: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
