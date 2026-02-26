from sqlalchemy import Column, String, Integer, DateTime, Numeric
from app.database.sessionManager import BaseModel_Base
import datetime

class StudentRecord(BaseModel_Base):
    __tablename__ = "student_records"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    student_id = Column(String(70), nullable=False, index=True)
    course_code = Column(String(50), nullable=False, index=True)
    semester = Column(String(100), nullable=False)
    assignment = Column(Numeric(5, 2), nullable=True, default=0)
    ca = Column(Numeric(5, 2), nullable=True, default=0)
    exam = Column(Numeric(5, 2), nullable=True, default=0)
    total_score = Column(Numeric(5, 2), nullable=True)
    letter_grade = Column(String(2), nullable=True)  # A, B, C, D, F
    gpa = Column(Numeric(3, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
