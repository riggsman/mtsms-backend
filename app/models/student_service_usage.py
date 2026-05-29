import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from app.database.base_model import BaseModel_Base


class StudentServiceUsage(BaseModel_Base):
    __tablename__ = "student_service_usage"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    service_key = Column(String(120), nullable=False, index=True)
    usage_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "student_id",
            "service_key",
            name="uq_student_service_usage",
        ),
    )

