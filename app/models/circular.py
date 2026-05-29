from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from app.database.base_model import BaseModel_Base
import datetime

class Circular(BaseModel_Base):
    __tablename__ = "circulars"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    attachment_path = Column(String(500), nullable=True)
    target_audience = Column(JSON, nullable=True)  # Roles or groups e.g. ["student", "staff"]
    posted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
