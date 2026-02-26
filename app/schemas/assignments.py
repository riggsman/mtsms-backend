from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

class AssignmentRequest(BaseModel):
    course_code: str
    title: str
    description: Optional[str] = None
    due_date: date
    extended_due_date: Optional[date] = None
    max_score: Optional[float] = None
    late_penalty: Optional[int] = 0
    created_by: str
    lecturer_id: Optional[int] = None  # Link to teacher/lecturer
    institution_id: Optional[int] = None  # Will be set from current_user if not provided

class AssignmentResponse(BaseModel):
    id: int
    institution_id: int
    lecturer_id: Optional[int]
    course_code: str
    title: str
    description: Optional[str]
    due_date: date
    extended_due_date: Optional[date]
    max_score: Optional[float]
    late_penalty: Optional[int]
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class AssignmentUpdate(BaseModel):
    course_code: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    extended_due_date: Optional[date] = None
    max_score: Optional[float] = None
    late_penalty: Optional[int] = None
    created_by: Optional[str] = None
    lecturer_id: Optional[int] = None

class AssignmentSubmissionRequest(BaseModel):
    assignment_id: int
    student_id: str
    submission_file: Optional[str] = None

class AssignmentSubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    student_id: str
    submission_file: Optional[str]
    submission_date: datetime
    status: str
    grade: Optional[str]
    feedback: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
