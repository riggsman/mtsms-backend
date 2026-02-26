from sqlalchemy import Column, String, Integer, DateTime, Text
from app.database.sessionManager import BaseModel_Base
import datetime

class Activity(BaseModel_Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    action = Column(String(100), nullable=False)  # e.g., "User Created", "Course Deleted", "Schedule Updated"
    entity_type = Column(String(50), nullable=False)  # e.g., "user", "course", "schedule", "student", "student_record"
    entity_id = Column(Integer, nullable=True)  # ID of the affected entity (if applicable)
    performed_by = Column(String(200), nullable=False)  # Name of the user who performed the action
    performer_role = Column(String(50), nullable=False)  # Role of the user who performed the action
    performer_id = Column(Integer, nullable=True)  # ID of the user who performed the action
    content = Column(Text, nullable=True)  # Additional details about the action (e.g., "Deleted user: Michael Brown (STU002)")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
