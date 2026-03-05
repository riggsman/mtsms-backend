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
    submitted_at: Optional[datetime] = None  # Alias for submission_date for frontend compatibility
    status: str
    grade: Optional[str]
    score: Optional[float] = None  # Alias for grade (converted to float if numeric)
    feedback: Optional[str]
    note: Optional[str] = None  # Additional note field for submissions
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
    
    def __init__(self, **data):
        # Map submission_date to submitted_at if not provided
        if 'submitted_at' not in data and 'submission_date' in data:
            data['submitted_at'] = data['submission_date']
        
        # Convert grade to score if grade is numeric
        if 'score' not in data and 'grade' in data and data.get('grade'):
            try:
                # Try to convert grade string to float
                data['score'] = float(data['grade'])
            except (ValueError, TypeError):
                # If conversion fails, leave score as None
                pass
        
        super().__init__(**data)