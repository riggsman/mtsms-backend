from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NoteCreate(BaseModel):
    title: str
    course_id: int
    course_code: Optional[str] = None
    department_id: int
    lecturer_id: Optional[int] = None  # Optional: required for admins, auto-filled for staff
    content: str  # Rich text content

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    course_id: Optional[int] = None
    course_code: Optional[str] = None
    department_id: Optional[int] = None
    content: Optional[str] = None

class NoteResponse(BaseModel):
    id: int
    institution_id: int
    title: str
    course_id: int
    course_code: Optional[str] = None
    department_id: int
    lecturer_id: int
    content: str
    pdf_file_path: Optional[str] = None
    word_file_path: Optional[str] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related data
    course_name: Optional[str] = None
    course_code_full: Optional[str] = None
    department_name: Optional[str] = None
    lecturer_name: Optional[str] = None

    class Config:
        from_attributes = True
