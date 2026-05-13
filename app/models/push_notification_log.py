from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from app.database.base import DefaultBase
import datetime


class PushNotificationLog(DefaultBase):
    """
    Log of all push notifications sent via the system.
    Stores the notification details and delivery status.
    """
    
    __tablename__ = "push_notification_logs"
    
    id = Column(Integer, primary_key=True)
    
    # Notification content
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    
    # Targeting info
    target_tenants = Column(JSON, nullable=True)  # List of tenant IDs or null for all
    target_roles = Column(JSON, nullable=True)     # List of roles or null for all
    
    # Status
    status = Column(String(50), nullable=False, default="pending")  # pending, sent, failed
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Failure reason (stored as JSON for flexibility)
    failure_reason = Column(JSON, nullable=True)
    
    # Metadata about the send operation
    send_metadata = Column(JSON, nullable=True)  # Extra info like tokens_targeted, etc.
    
    # Who sent it (system admin user ID)
    sent_by_user_id = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    
    def mark_as_sent(self, success: int = 0, failure: int = 0, reason: dict = None):
        """Mark the notification as sent with results."""
        self.status = "sent"
        self.success_count = success
        self.failure_count = failure
        if reason:
            self.failure_reason = reason
        self.sent_at = datetime.datetime.utcnow()
    
    def mark_as_failed(self, reason: dict):
        """Mark the notification as failed."""
        self.status = "failed"
        self.failure_reason = reason
        self.sent_at = datetime.datetime.utcnow()