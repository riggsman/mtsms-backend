from sqlalchemy import Column, String, Integer, DateTime, Date
import datetime

from app.database.sessionManager import BaseModel_Base


class StudentAttendanceEntry(BaseModel_Base):
    """Per-session class attendance for a student (matricule = students.student_id)."""

    __tablename__ = "student_attendance_entries"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    student_id = Column(String(70), nullable=False, index=True)
    course_code = Column(String(50), nullable=False)
    session_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="present")  # present, absent, late, excused
    notes = Column(String(500), nullable=True)
    recorded_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
    deleted_at = Column(DateTime, nullable=True)
