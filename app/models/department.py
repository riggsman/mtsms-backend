from sqlalchemy import Column, String, Integer, DateTime, Text
from app.database.sessionManager import BaseModel_Base
import datetime

class Department(BaseModel_Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    head_id = Column(Integer, nullable=True)  # Teacher ID who is the head
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
