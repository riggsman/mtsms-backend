from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from app.database.sessionManager import BaseModel_Base
import datetime

class Complaint(BaseModel_Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    student_id = Column(String(70), nullable=False, index=True)
    complaint_type = Column(String(100), nullable=False)  # academic_record, lecturer, etc.
    caption = Column(String(200), nullable=False)
    contents = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False, nullable=False)
    screenshots = Column(Text, nullable=True)  # JSON array of base64 images
    status = Column(String(50), default="pending", nullable=False)  # pending, addressed
    resolved_by = Column(String(200), nullable=True)
    resolver_role = Column(String(50), nullable=True)
    resolved_date = Column(DateTime, nullable=True)
    submission_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
