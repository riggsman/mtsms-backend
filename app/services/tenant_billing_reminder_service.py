"""
Send billing reminder emails to premium tenants 5 days before next billing date.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.apis.tenant import _add_institution_contact, _is_premium_plan
from app.helpers.logger import logger
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant import Tenant
from app.models.tenant_billing_reminder import TenantBillingReminder
from app.schemas.tenant import TenantResponse
from app.services.email_service import EmailService

REMINDER_DAYS_BEFORE = 5


class TenantBillingReminderService:
    def __init__(self, db: Session):
        self.db = db

    def _reminder_already_sent(self, tenant_id: int, billing_due: datetime) -> bool:
        due_norm = billing_due.replace(hour=0, minute=0, second=0, microsecond=0)
        row = (
            self.db.query(TenantBillingReminder)
            .filter(
                TenantBillingReminder.tenant_id == tenant_id,
                TenantBillingReminder.billing_due_date == due_norm,
            )
            .first()
        )
        return row is not None

    def _record_reminder(
        self,
        tenant_id: int,
        billing_due: datetime,
        recipient_email: str,
        status: str = "sent",
        error_message: Optional[str] = None,
    ) -> None:
        due_norm = billing_due.replace(hour=0, minute=0, second=0, microsecond=0)
        self.db.add(
            TenantBillingReminder(
                tenant_id=tenant_id,
                billing_due_date=due_norm,
                recipient_email=recipient_email,
                status=status,
                error_message=error_message,
            )
        )

    def _plan_amount_label(self, tenant: Tenant) -> Optional[str]:
        if not tenant.subscription_plan:
            return None
        plan = (
            self.db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.name == tenant.subscription_plan)
            .first()
        )
        if not plan:
            return None
        period = plan.billing_period or "cycle"
        try:
            price = float(plan.price)
        except (TypeError, ValueError):
            price = 0
        return f"${price:.2f} / {period}"

    async def send_billing_reminders(self, days_before: int = REMINDER_DAYS_BEFORE) -> int:
        """Send reminders when next billing is exactly ``days_before`` days away."""
        today = datetime.now(timezone.utc).date()
        sent_count = 0
        pending_commit = False

        tenants = (
            self.db.query(Tenant)
            .filter(Tenant.subscription_plan.isnot(None), Tenant.is_active.is_(True))
            .all()
        )

        for tenant in tenants:
            if not _is_premium_plan(tenant.subscription_plan):
                continue

            response = TenantResponse.model_validate(tenant, from_attributes=True)
            next_billing = response.next_subscription_date
            if not next_billing:
                continue

            due_date = (
                next_billing.date()
                if hasattr(next_billing, "date")
                else next_billing
            )
            days_until = (due_date - today).days
            if days_until != days_before:
                continue

            tenant_contact = _add_institution_contact(self.db, tenant)
            recipient = (getattr(tenant_contact, "email", None) or "").strip()
            if not recipient:
                logger.warning(
                    "Skipping billing reminder for tenant %s: no admin email",
                    tenant.name,
                )
                continue

            billing_due_dt = (
                next_billing
                if isinstance(next_billing, datetime)
                else datetime.combine(due_date, datetime.min.time())
            )
            if self._reminder_already_sent(tenant.id, billing_due_dt):
                continue

            billing_type_label = (tenant.billing_type or "monthly").capitalize()
            due_str = due_date.strftime("%B %d, %Y")

            try:
                ok = await EmailService.send_tenant_billing_reminder_email(
                    tenant_name=tenant.name,
                    admin_email=recipient,
                    billing_due_date=due_str,
                    days_remaining=days_before,
                    subscription_plan=tenant.subscription_plan,
                    billing_type=billing_type_label,
                    amount_label=self._plan_amount_label(tenant),
                )
                if ok:
                    self._record_reminder(tenant.id, billing_due_dt, recipient, status="sent")
                    sent_count += 1
                else:
                    self._record_reminder(
                        tenant.id,
                        billing_due_dt,
                        recipient,
                        status="failed",
                        error_message="Email send returned false",
                    )
                pending_commit = True
            except Exception as exc:
                logger.error(
                    "Billing reminder failed for tenant %s: %s",
                    tenant.name,
                    exc,
                )
                self._record_reminder(
                    tenant.id,
                    billing_due_dt,
                    recipient,
                    status="failed",
                    error_message=str(exc)[:500],
                )
                pending_commit = True

        if pending_commit:
            self.db.commit()
        return sent_count

    def send_billing_reminders_sync(self, days_before: int = REMINDER_DAYS_BEFORE) -> int:
        try:
            return asyncio.run(self.send_billing_reminders(days_before=days_before))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self.send_billing_reminders(days_before=days_before)
                )
            finally:
                loop.close()
