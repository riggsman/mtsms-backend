from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from app.database.base import DefaultBase
import datetime

class Department(DefaultBase):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)  # Multi-tenancy isolation
    school_id = Column(Integer, nullable=True, index=True)  # logical FK to schools.id (no DB constraint for migration flexibility)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    head_id = Column(Integer, nullable=True)  # Teacher ID who is the head
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
