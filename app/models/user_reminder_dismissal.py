"""
Model for tracking user reminder dismissals
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Index
from app.database.sessionManager import BaseModel_Base
import datetime


class UserReminderDismissal(BaseModel_Base):
    """Track which reminders users have dismissed"""
    
    __tablename__ = "user_reminder_dismissals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    reminder_id = Column(Integer, ForeignKey('schedule_reminders.id'), nullable=False, index=True)
    dismissed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Composite unique index to prevent duplicate dismissals
    __table_args__ = (
        Index('ix_user_reminder_dismissal_unique', 'user_id', 'reminder_id', unique=True),
    )
