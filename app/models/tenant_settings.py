from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean
from app.database.sessionManager import BaseModel_Base
import datetime

class TenantSettings(BaseModel_Base):
    __tablename__ = "tenant_settings"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, unique=True, index=True)  # One settings per tenant
    matricule_format = Column(JSON, nullable=True)  # Store format configuration as JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
