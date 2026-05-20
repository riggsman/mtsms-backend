from sqlalchemy import Column, Integer, Boolean, String, Text, DateTime
from app.database.base import DefaultBase
import datetime


class SystemSettings(DefaultBase):
    """
    Global system-level settings for the platform (one row, id=1).
    Used by the system admin UI at /admin/system-settings.
    """

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True)

    maintenance_mode = Column(Boolean, default=False, nullable=False)
    allow_new_registrations = Column(Boolean, default=True, nullable=False)
    max_tenants = Column(Integer, default=100, nullable=False)
    session_timeout = Column(Integer, default=30, nullable=False)
    email_notifications = Column(Boolean, default=True, nullable=False)

    # Caching and inactivity configuration (in minutes)
    cache_timeout = Column(Integer, default=5, nullable=False)
    inactivity_timeout = Column(Integer, default=5, nullable=False)
    maintenance_check_interval = Column(Integer, default=60, nullable=False)
    
    # Token expiration configuration
    access_token_expire_minutes = Column(Integer, default=60, nullable=False)
    refresh_token_expire_days = Column(Integer, default=1, nullable=False)

    # Cache version for frontend cache synchronization
    # This value increments whenever a force-apply is triggered,
    # allowing all frontend clients to detect the change and refresh their caches
    cache_version = Column(String(64), default="1", nullable=False)

    # System logo URL
    logo_url = Column(String(500), nullable=True)

    # Firebase Cloud Messaging configuration for push notifications
    firebase_messaging_enabled = Column(Boolean, default=False, nullable=False)
    firebase_api_key = Column(String(500), nullable=True)
    firebase_auth_domain = Column(String(255), nullable=True)
    firebase_project_id = Column(String(255), nullable=True)
    firebase_messaging_sender_id = Column(String(255), nullable=True)
    firebase_app_id = Column(String(255), nullable=True)
    firebase_vapid_key = Column(String(500), nullable=True)
    firebase_storage_bucket = Column(String(255), nullable=True)
    firebase_measurement_id = Column(String(255), nullable=True)
    firebase_service_account_uploaded = Column(Boolean, default=False, nullable=False)

    platform_support_email = Column(String(255), nullable=True)
    platform_support_phone = Column(String(50), nullable=True)
    platform_support_hours = Column(String(255), nullable=True)

    created_at = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

