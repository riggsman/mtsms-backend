from sqlalchemy import Column, String, Integer, DateTime, Text, Time
from app.database.sessionManager import BaseModel_Base
import datetime

class Schedule(BaseModel_Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    course_name = Column(String(200), nullable=False)
    instructor = Column(String(200), nullable=False)
    day = Column(String(50), nullable=False)  # Monday, Tuesday, etc.
    start_time = Column(String(10), nullable=False)  # Format: HH:MM
    end_time = Column(String(10), nullable=False)  # Format: HH:MM
    room = Column(String(100), nullable=True)
    capacity = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
