from sqlalchemy import Column, String, Integer, DateTime, Boolean
from app.database.sessionManager import BaseModel_Base
import datetime

class Class(BaseModel_Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)  # Class code (e.g., "l1", "L1", "Level 1")
    institution_level = Column(String(10), nullable=False, default="HI")  # HI (Higher Institution) or SI (Secondary Institution)
    category = Column(String(50), nullable=True)  # Category for the class
    is_custom = Column(Boolean, default=True, nullable=False)  # True for custom classes, False for default classes
    level_id = Column(Integer, nullable=True)  # Made nullable as it may not be needed with code
    department_id = Column(Integer, nullable=True)
    academic_year_id = Column(Integer, nullable=True)  # Made nullable for flexibility
    capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
