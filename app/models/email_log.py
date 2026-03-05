from sqlalchemy import Column, DateTime, String, Integer, Text, Enum as SQLEnum
from app.database.sessionManager import BaseModel_Base
import datetime
import enum

class EmailStatus(enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"
    BOUNCED = "BOUNCED"

class EmailLog(BaseModel_Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True, index=True)
    sender_email = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, SENT, FAILED, DELIVERED, BOUNCED
    failure_reason = Column(Text, nullable=True)
    provider_message_id = Column(String(255), nullable=True, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    institution_id = Column(Integer, nullable=True, index=True)  # For tenant isolation
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=True)
