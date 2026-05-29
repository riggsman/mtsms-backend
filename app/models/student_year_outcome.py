import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base_model import BaseModel_Base


class StudentYearOutcome(BaseModel_Base):
    __tablename__ = "student_year_outcomes"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    academic_year_id = Column(Integer, nullable=False, index=True)
    term = Column(String(20), nullable=True)
    final_status = Column(String(30), nullable=False, index=True)  # promoted|repeated|graduated|transferred
    notes = Column(Text, nullable=True)
    decided_by = Column(Integer, nullable=True)
    decided_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
