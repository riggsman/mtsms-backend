from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database.base_model import BaseModel_Base
import datetime


class StudentUploadedDocument(BaseModel_Base):
    __tablename__ = "student_uploaded_documents"

    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(120), nullable=True)
    file_size = Column(Integer, nullable=False, default=0)
    document_kind = Column(String(40), nullable=False, default="general")  # general | id_card
    document_side = Column(String(20), nullable=True)  # front | back for id_card
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
