from sqlalchemy import Column, String, Integer, DateTime, Text, Date, Numeric
from app.database.sessionManager import BaseModel_Base
import datetime

class Assignment(BaseModel_Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    lecturer_id = Column(Integer, nullable=True, index=True)  # Link to teacher/lecturer
    course_code = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=False)
    extended_due_date = Column(Date, nullable=True)
    max_score = Column(Numeric(10, 2), nullable=True)  # Maximum score for the assignment
    late_penalty = Column(Integer, nullable=True, default=0)  # Percentage penalty
    created_by = Column(String(200), nullable=False)  # Instructor/Admin name
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete

class AssignmentSubmission(BaseModel_Base):
    __tablename__ = "assignment_submissions"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    assignment_id = Column(Integer, nullable=False, index=True)
    student_id = Column(String(70), nullable=False, index=True)
    submission_file = Column(Text, nullable=True)  # Base64 or file path
    submission_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(50), default="submitted", nullable=False)  # submitted, late, graded
    grade = Column(String(10), nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
