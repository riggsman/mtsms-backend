from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from app.database.sessionManager import BaseModel_Base
import datetime

class StaffDocument(BaseModel_Base):
    __tablename__ = "staff_documents"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_type = Column(String(50), nullable=False)  # ID, Transcript, Certification, CV, Contract, Other
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    issue_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    document_side = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
