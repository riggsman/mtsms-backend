from sqlalchemy import Column, DateTime, Integer, ForeignKey, Numeric, String
from app.database.sessionManager import BaseModel_Base
import datetime


class PayrollTimeEntry(BaseModel_Base):
    __tablename__ = "payroll_time_entries"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    course_code_snapshot = Column(String(50), nullable=True, index=True)
    clock_in_code_hash = Column(String(255), nullable=True)
    clock_out_code_hash = Column(String(255), nullable=True)
    clock_in_code_plain = Column(String(5), nullable=True)
    clock_out_code_plain = Column(String(5), nullable=True)
    codes_generated_by_user_id = Column(Integer, nullable=True)
    codes_generated_at = Column(DateTime, nullable=True)
    codes_expires_at = Column(DateTime, nullable=True)
    clock_in_code_used_at = Column(DateTime, nullable=True)
    clock_out_code_used_at = Column(DateTime, nullable=True)
    clock_in_at = Column(DateTime, nullable=False)
    clock_out_at = Column(DateTime, nullable=True)
    lecturer_clock_out_confirmed_at = Column(DateTime, nullable=True)
    student_clock_out_confirmed_at = Column(DateTime, nullable=True)
    student_confirmer_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    clock_out_finalized_at = Column(DateTime, nullable=True)
    duration_hours = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
    deleted_at = Column(DateTime, nullable=True)
