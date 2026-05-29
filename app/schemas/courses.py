from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime

class CourseRequest(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    department_id: int
    level_id: Optional[int] = None
    instructor_id: Optional[int] = None
    # Stores semester ID from global system semester setup.
    semester: Optional[int] = Field(None, ge=1)
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
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
    instructor_id: Optional[int] = None
    credits: Optional[Decimal]
    semester: Optional[int] = None
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
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
    instructor_id: Optional[int] = None
    credits: Optional[Decimal] = None
    semester: Optional[int] = Field(None, ge=1)
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None

class CourseSchedulePerformanceItem(BaseModel):
    id: int
    day: str
    start_time: str
    end_time: str
    room: Optional[str] = None
    instructor: Optional[str] = None
    hours: Decimal

class CoursePerformanceResponse(BaseModel):
    id: int
    institution_id: int
    code: str
    name: str
    department_id: int
    department_name: Optional[str] = None
    semester: Optional[int] = None
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    instructors: List[str] = Field(default_factory=list)
    expected_teaching_hours: Decimal
    elapsed_scheduled_hours: Decimal
    progress_percentage: Decimal
    registered_students: int
    exam_written_students: int
    passed_students: int
    pass_rate_percentage: Decimal
    exam_participation_percentage: Decimal
    schedules: List[CourseSchedulePerformanceItem] = Field(default_factory=list)
