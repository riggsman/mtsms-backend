from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CourseInfo(BaseModel):
    """Course information for schedule response"""
    id: Optional[int] = None
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

class InstructorInfo(BaseModel):
    """Instructor/Teacher information for schedule response"""
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[str] = None

class ScheduleRequest(BaseModel):
    course_name: str
    instructor: str
    day: str
    start_time: str
    end_time: str
    room: Optional[str] = None
    capacity: Optional[int] = None
    description: Optional[str] = None
    institution_id: Optional[int] = None  # For tenant isolation

class ScheduleResponse(BaseModel):
    id: int
    institution_id: int  # For tenant isolation
    course_name: str
    instructor: str
    day: str
    start_time: str
    end_time: str
    room: Optional[str]
    capacity: Optional[int]
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    # Enriched data
    course_info: Optional[CourseInfo] = None
    instructor_info: Optional[InstructorInfo] = None

    class Config:
        from_attributes = True

class ScheduleUpdate(BaseModel):
    course_name: Optional[str] = None
    instructor: Optional[str] = None
    day: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    room: Optional[str] = None
    capacity: Optional[int] = None
    description: Optional[str] = None
