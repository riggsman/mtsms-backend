from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DepartmentRequest(BaseModel):
    name: str = Field(..., description="Department name")
    code: str = Field(..., description="Department code (unique)")
    description: Optional[str] = Field(None, description="Department description")
    head_id: Optional[int] = Field(None, description="Teacher ID who is the department head")
    institution_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    head_id: Optional[int] = None


class DepartmentResponse(BaseModel):
    id: int
    institution_id: int
    name: str
    code: str
    description: Optional[str] = None
    head_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
