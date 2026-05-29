from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database.base_model import BaseModel_Base
import datetime


class GradingMethod(BaseModel_Base):
    """
    Grading scale for a tenant (institution) or the platform-wide default.

    When institution_id is NULL and is_system_default is True, this row is the
    fallback grading system for tenants without their own configuration.
    """

    __tablename__ = "grading_methods"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    institution_id = Column(Integer, nullable=True, unique=True)
    is_system_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    grading_ranges = relationship(
        "GradingRange",
        back_populates="grading_method",
        cascade="all, delete-orphan",
        order_by="GradingRange.minimum_score",
    )


class GradingRange(BaseModel_Base):
    __tablename__ = "grading_ranges"

    id = Column(Integer, primary_key=True)
    grading_method_id = Column(
        Integer,
        ForeignKey("grading_methods.id", ondelete="CASCADE"),
        nullable=False,
    )
    minimum_score = Column(Float, nullable=False)
    maximum_score = Column(Float, nullable=False)
    grade = Column(String(10), nullable=False)
    grade_point = Column(Float, nullable=False)

    grading_method = relationship("GradingMethod", back_populates="grading_ranges")
