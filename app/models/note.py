from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from app.database.sessionManager import BaseModel_Base
import datetime

class Note(BaseModel_Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, index=True)  # Multi-tenancy isolation
    title = Column(String(200), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False, index=True)
    course_code = Column(String(50), nullable=True)  # Optional course code
    department_id = Column(Integer, nullable=False, index=True)
    lecturer_id = Column(Integer, ForeignKey('teachers.id'), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Rich text content
    pdf_file_path = Column(String(500), nullable=True)  # Path to PDF file
    word_file_path = Column(String(500), nullable=True)  # Path to Word file
    created_by = Column(Integer, nullable=False)  # User ID who created the note
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
