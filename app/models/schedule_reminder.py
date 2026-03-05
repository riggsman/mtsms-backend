"""
Model for tracking schedule reminders to avoid duplicate emails
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from app.database.sessionManager import BaseModel_Base
import datetime


class ScheduleReminder(BaseModel_Base):
    """Track sent schedule reminders to avoid duplicates"""
    
    __tablename__ = "schedule_reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey('schedules.id'), nullable=False, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    reminder_type = Column(String(20), nullable=False)  # 'instructor' or 'student'
    recipient_email = Column(String(255), nullable=False, index=True)
    reminder_time = Column(DateTime, nullable=False)  # When the reminder was sent
    class_start_time = Column(DateTime, nullable=False)  # When the class actually starts
    sent_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(20), default='sent', nullable=False)  # 'sent', 'failed'
    error_message = Column(String(500), nullable=True)
    
    # Composite index to prevent duplicate reminders
    __table_args__ = (
        Index('ix_schedule_reminder_unique', 'schedule_id', 'reminder_type', 'recipient_email', 'class_start_time', unique=True),
    )
