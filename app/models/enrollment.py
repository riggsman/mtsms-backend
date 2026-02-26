from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database.sessionManager import BaseModel_Base
import datetime

class Enrollment(BaseModel_Base):
    """
    Student course enrollment model.
    Tracks which courses a student is registered for.
    """
    __tablename__ = "enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    enrollment_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, completed, dropped
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Unique constraint to prevent duplicate enrollments
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
