from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from app.database.base import DefaultBase
import datetime

class SystemConfig(DefaultBase):
    """
    System configuration model stored in the global database.
    Used to store system-wide settings like database architecture mode.
    """
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)  # Changed from String(500) to Text to support longer JSON
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
