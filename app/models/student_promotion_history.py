import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.sessionManager import BaseModel_Base


class StudentPromotionHistory(BaseModel_Base):
    __tablename__ = "student_promotion_history"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    academic_year_id = Column(Integer, nullable=False, index=True)
    from_class_id = Column(Integer, nullable=False, index=True)
    to_class_id = Column(Integer, nullable=True, index=True)
    final_status = Column(String(30), nullable=False, index=True)
    archived_student_snapshot = Column(Text, nullable=True)
    archived_enrollment_snapshot = Column(Text, nullable=True)
    promoted_by = Column(Integer, nullable=True)
    promoted_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    execution_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
