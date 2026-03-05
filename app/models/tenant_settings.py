from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean
from app.database.sessionManager import BaseModel_Base
import datetime

class TenantSettings(BaseModel_Base):
    __tablename__ = "tenant_settings"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, nullable=False, unique=True, index=True)  # One settings per tenant
    matricule_format = Column(JSON, nullable=True)  # Store format configuration as JSON
    is_matricule_format_set = Column(Boolean, default=False, nullable=False)  # Flag to indicate if matricule format is configured
    logo = Column(String(500), nullable=True)  # Path to tenant logo file
    email_reminder_time = Column(Integer, nullable=True, default=30)  # Minutes before class to send reminder (default: 30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
