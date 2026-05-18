"""Platform-wide analytics events (shared database / DefaultBase)."""

import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import DefaultBase


class LoginAuditEvent(DefaultBase):
    __tablename__ = "login_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    tenant_name = Column(String(70), nullable=True)
    user_id = Column(Integer, nullable=True)
    identifier = Column(String(255), nullable=True)
    method = Column(String(32), nullable=False, index=True)
    outcome = Column(String(16), nullable=False, index=True)
    failure_reason = Column(String(64), nullable=True, index=True)
    failure_detail = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)


class OtpAuditEvent(DefaultBase):
    __tablename__ = "otp_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    tenant_name = Column(String(70), nullable=True)
    user_id = Column(Integer, nullable=True)
    event_type = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)


class PlatformEmailEvent(DefaultBase):
    __tablename__ = "platform_email_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, index=True)
    failure_reason = Column(Text, nullable=True)
    email_category = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)


class PlatformErrorEvent(DefaultBase):
    __tablename__ = "platform_error_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    tenant_name = Column(String(70), nullable=True)
    user_id = Column(Integer, nullable=True)
    source = Column(String(32), nullable=False, index=True)
    error_type = Column(String(64), nullable=True, index=True)
    message = Column(Text, nullable=False)
    status_code = Column(Integer, nullable=True, index=True)
    method = Column(String(10), nullable=True)
    path = Column(String(512), nullable=True)
    route_template = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)


class ApiRequestLog(DefaultBase):
    __tablename__ = "api_request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    tenant_name = Column(String(70), nullable=True)
    user_id = Column(Integer, nullable=True)
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False)
    route_template = Column(String(512), nullable=True, index=True)
    status_code = Column(Integer, nullable=False, index=True)
    duration_ms = Column(Integer, nullable=True)
    billing_category = Column(String(32), nullable=False, default="api")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
