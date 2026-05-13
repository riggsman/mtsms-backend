from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from app.database.sessionManager import BaseModel_Base
import datetime

class CommunicationTemplate(BaseModel_Base):
    __tablename__ = "communication_templates"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    subject_template = Column(String(255), nullable=True)
    content_template = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)  # academic, finance, admin, etc.
    variables = Column(JSON, nullable=True)  # List of available variables e.g. ["student_name", "amount_due"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
