from sqlalchemy import Column, String, Integer, DateTime, Boolean
from app.database.base import DefaultBase
import datetime

class Tenant(DefaultBase):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(70), nullable=False, unique=True)
    category = Column(String(10), nullable=False)  # HI or SI
    database_url = Column(String(200), nullable=True)
    domain = Column(String(200), nullable=True)
    logo_url = Column(String(500), nullable=True)  # URL to tenant logo file
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)