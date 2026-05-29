"""Academic calendar entries (DATE + ACTIVITIES) per tenant and academic year."""
import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Text, Index

from app.database.base_model import BaseModel_Base


class AcademicCalendar(BaseModel_Base):
    __tablename__ = "academic_calendar"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    academic_year_id = Column(Integer, nullable=False, index=True)
    event_date = Column(Date, nullable=False)
    event_end_date = Column(Date, nullable=False)
    activity = Column(Text, nullable=False)
    row_order = Column(Integer, nullable=False, default=0)
    source_filename = Column(String(255), nullable=True)
    uploaded_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=True,
    )
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index(
            "uq_academic_calendar_inst_year_date_range",
            "institution_id",
            "academic_year_id",
            "event_date",
            "event_end_date",
            unique=True,
        ),
    )
