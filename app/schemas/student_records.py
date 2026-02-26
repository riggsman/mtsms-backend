from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

class StudentRecordRequest(BaseModel):
    student_id: str
    course_code: str
    semester: str
    assignment: Optional[Decimal] = None
    ca: Optional[Decimal] = None
    exam: Optional[Decimal] = None

class StudentRecordResponse(BaseModel):
    id: int
    student_id: str
    course_code: str
    semester: str
    assignment: Optional[Decimal]
    ca: Optional[Decimal]
    exam: Optional[Decimal]
    total_score: Optional[Decimal]
    letter_grade: Optional[str]
    gpa: Optional[Decimal]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class StudentRecordUpdate(BaseModel):
    student_id: Optional[str] = None
    course_code: Optional[str] = None
    semester: Optional[str] = None
    assignment: Optional[Decimal] = None
    ca: Optional[Decimal] = None
    exam: Optional[Decimal] = None
