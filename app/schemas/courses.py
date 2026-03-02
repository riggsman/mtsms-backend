from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class CourseRequest(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    department_id: int
    level_id: Optional[int] = None
    credits: Optional[Decimal] = None
    institution_id: Optional[int] = None

class CourseResponse(BaseModel):
    id: int
    institution_id: int
    name: str
    code: str
    description: Optional[str]
    department_id: int
    department_name: Optional[str] = None  # Department name from departments table
    level_id: Optional[int]
    credits: Optional[Decimal]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    level_id: Optional[int] = None
    credits: Optional[Decimal] = None