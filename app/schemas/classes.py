from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ClassRequest(BaseModel):
    name: str = Field(..., description="Class name (e.g., 'Level 1', 'Grade 10')")
    code: str = Field(..., description="Class code (e.g., 'l1', 'L1', 'G10')")
    institution_level: str = Field(default="HI", description="Institution level: HI (Higher Institution) or SI (Secondary Institution)")
    category: Optional[str] = Field(None, description="Category for the class (e.g., 'Science', 'Arts', etc.)")
    institution_id: Optional[int] = None
    level_id: Optional[int] = None
    department_id: Optional[int] = None
    academic_year_id: Optional[int] = None
    capacity: Optional[int] = None

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    institution_level: Optional[str] = None
    level_id: Optional[int] = None
    department_id: Optional[int] = None
    academic_year_id: Optional[int] = None
    capacity: Optional[int] = None
    category: Optional[str] = None  # e.g., 'Science', 'Arts', etc.

class ClassResponse(BaseModel):
    id: int
    institution_id: int
    name: str
    code: str  # Class code displayed in code section
    institution_level: str
    category: Optional[str] = None  # Category for the class (e.g., 'Science', 'Arts', etc.)
    is_custom: bool = True  # True for custom classes, False for default classes
    level_id: Optional[int] = None
    level: Optional[str] = None  # Level name displayed in level section
    level_code: Optional[str] = None  # Level code if available
    department_id: Optional[int] = None
    academic_year_id: Optional[int] = None
    capacity: Optional[int] = None
    created_at: Optional[datetime] = None  # Made optional for default classes
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
