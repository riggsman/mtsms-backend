from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SpecializationRequest(BaseModel):
    name: str = Field(..., description="Specialization name")
    code: str = Field(..., description="Specialization code (unique)")
    description: Optional[str] = Field(None, description="Specialization description")
    department_id: int = Field(..., description="Department ID this specialization belongs to")
    head_id: Optional[int] = Field(None, description="Teacher ID who heads this specialization")
    institution_id: Optional[int] = None


class SpecializationUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    head_id: Optional[int] = None


class SpecializationResponse(BaseModel):
    id: int
    institution_id: int
    department_id: int
    name: str
    code: str
    description: Optional[str] = None
    head_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
