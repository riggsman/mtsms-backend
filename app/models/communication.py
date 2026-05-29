from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from app.database.base_model import BaseModel_Base
import datetime

class Communication(BaseModel_Base):
    __tablename__ = "communications"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel = Column(String(20), nullable=False)  # email, sms, push
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    # Audience details
    recipient_type = Column(String(50), nullable=False)  # role, department, class, individual
    recipient_filter = Column(JSON, nullable=True)  # Filter parameters used
    total_recipients = Column(Integer, default=0)
    # Status
    status = Column(String(20), default="sent")  # sent, failed, partially_failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
