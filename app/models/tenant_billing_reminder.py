"""Track sent tenant subscription billing reminders (global DB)."""
import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String

from app.database.base import DefaultBase


class TenantBillingReminder(DefaultBase):
    __tablename__ = "tenant_billing_reminders"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    billing_due_date = Column(DateTime, nullable=False)
    recipient_email = Column(String(255), nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(20), default="sent", nullable=False)
    error_message = Column(String(500), nullable=True)

    __table_args__ = (
        Index(
            "ix_tenant_billing_reminder_unique",
            "tenant_id",
            "billing_due_date",
            unique=True,
        ),
    )
