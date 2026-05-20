"""Audit trail for tenant lifecycle actions (suspend, resume, activation)."""

import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.base import DefaultBase


class TenantAuditEvent(DefaultBase):
    __tablename__ = "tenant_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    action = Column(String(32), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    actor_user_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
