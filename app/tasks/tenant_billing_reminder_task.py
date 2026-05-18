"""
Daily task: email premium tenants 5 days before subscription billing is due.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database.base import get_db_session
from app.helpers.logger import logger
from app.services.tenant_billing_reminder_service import TenantBillingReminderService

billing_scheduler = BackgroundScheduler()


def send_tenant_billing_reminders():
    try:
        db = next(get_db_session())
        try:
            service = TenantBillingReminderService(db)
            count = service.send_billing_reminders_sync(days_before=5)
            if count:
                logger.info("Sent %s tenant billing reminder email(s)", count)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Error in tenant billing reminder task: %s", exc)


def start_tenant_billing_reminder_scheduler():
    try:
        if billing_scheduler.running:
            return
        billing_scheduler.add_job(
            send_tenant_billing_reminders,
            trigger=CronTrigger(hour=8, minute=0),
            id="tenant_billing_reminder_job",
            name="Tenant subscription billing reminders (5 days before due)",
            replace_existing=True,
        )
        billing_scheduler.start()
        logger.info(
            "Tenant billing reminder scheduler started (daily at 08:00 UTC)"
        )
    except Exception as exc:
        logger.error("Failed to start tenant billing reminder scheduler: %s", exc)


def stop_tenant_billing_reminder_scheduler():
    try:
        if billing_scheduler.running:
            billing_scheduler.shutdown(wait=False)
    except Exception as exc:
        logger.error("Error stopping tenant billing reminder scheduler: %s", exc)
