"""
Pydantic schemas for schedule reminders
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ReminderStatusResponse(BaseModel):
    """Response model for reminder status"""
    schedule_id: int
    course_name: str
    instructor: str
    day: str
    start_time: str
    end_time: str
    room: Optional[str]
    class_start_time: datetime
    instructor_reminder_sent: bool
    instructor_email: Optional[str]
    student_reminders_sent: int
    total_enrolled_students: int
    reminder_sent_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserReminderResponse(BaseModel):
    """Response model for user reminders"""
    id: int
    schedule_id: int
    course_name: str
    instructor: str
    day: str
    start_time: str
    end_time: str
    room: Optional[str]
    class_start_time: datetime
    reminder_time: datetime
    is_dismissed: bool
    
    class Config:
        from_attributes = True


class DismissReminderRequest(BaseModel):
    """Request model for dismissing a reminder"""
    reminder_id: int
