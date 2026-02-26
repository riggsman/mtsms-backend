from sqlalchemy import Column, String, Integer, DateTime, Text
from app.database.sessionManager import BaseModel_Base
import datetime

class Announcement(BaseModel_Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    target_audience = Column(String(20), nullable=False, default="all")  # "students", "staff", or "all"
    created_by = Column(Integer, nullable=False)  # User ID who created the announcement
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
