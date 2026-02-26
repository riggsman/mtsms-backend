from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EnrollmentBase(BaseModel):
    student_id: int
    course_id: int
    status: Optional[str] = "active"

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentUpdate(BaseModel):
    status: Optional[str] = None

class EnrollmentResponse(EnrollmentBase):
    id: int
    enrollment_date: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class EnrollmentWithCourse(EnrollmentResponse):
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    department_name: Optional[str] = None
