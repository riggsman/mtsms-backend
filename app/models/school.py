"""
School model — faculties/schools within an institution (e.g. Engineering, Business).
SchoolFee — per-school, per-level fee rows used by the schools API.
"""
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import DefaultBase


class School(DefaultBase):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    fees = relationship("SchoolFee", back_populates="school", cascade="all, delete-orphan")


class SchoolFee(DefaultBase):
    __tablename__ = "school_fees"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20), nullable=False)
    academic_year_id = Column(Integer, nullable=True, index=True)
    fee_amount = Column(Numeric(10, 2), nullable=False, default=0)
    fee_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)

    school = relationship("School", back_populates="fees")

    __table_args__ = (
        Index("ix_school_fees_school_level", "school_id", "level", unique=True),
        Index("ix_school_fees_academic_year_id", "academic_year_id"),
    )
