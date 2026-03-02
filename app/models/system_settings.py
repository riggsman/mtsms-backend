from sqlalchemy import Column, Integer, Boolean, String, Text, DateTime
from app.database.base import DefaultBase
import datetime


class SystemSettings(DefaultBase):
    """
    Global system-level settings for the platform (one row, id=1).
    Used by the system admin UI at /admin/system-settings.
    """

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    maintenance_mode = Column(Boolean, default=False, nullable=False)
    allow_new_registrations = Column(Boolean, default=True, nullable=False)
    max_tenants = Column(Integer, default=100, nullable=False)
    session_timeout = Column(Integer, default=30, nullable=False)
    email_notifications = Column(Boolean, default=True, nullable=False)

    # Firebase Cloud Messaging configuration for push notifications
    firebase_messaging_enabled = Column(Boolean, default=False, nullable=False)
    firebase_api_key = Column(String(500), nullable=True)
    firebase_auth_domain = Column(String(255), nullable=True)
    firebase_project_id = Column(String(255), nullable=True)
    firebase_messaging_sender_id = Column(String(255), nullable=True)
    firebase_app_id = Column(String(255), nullable=True)
    firebase_vapid_key = Column(String(500), nullable=True)

    created_at = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

