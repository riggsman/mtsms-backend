"""
Scheduled task for sending class reminder emails
"""
import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.database.base import get_db_session
from app.helpers.logger import logger
from app.services.schedule_reminder_service import ScheduleReminderService


# Global scheduler instance
scheduler = BackgroundScheduler()


def send_class_reminders():
    """
    Task function to send class reminder emails.
    Runs every minute to check for classes starting at configured reminder times.
    """
    db: Session | None = None
    try:
        db = next(get_db_session())
        reminder_service = ScheduleReminderService(db)
        try:
            reminder_service.auto_generate_payroll_codes_from_schedule()
        except Exception as exc:
            logger.error(
                "Error auto-generating payroll codes from schedules: %s",
                exc,
            )

        reminder_times = reminder_service.collect_reminder_times()

        async def _run_all_reminders():
            for minutes_ahead in reminder_times:
                try:
                    await reminder_service.send_reminders_for_upcoming_classes(
                        minutes_ahead=minutes_ahead
                    )
                except Exception as exc:
                    logger.error(
                        "Error sending reminders for %s minutes: %s",
                        minutes_ahead,
                        exc,
                    )

        asyncio.run(_run_all_reminders())
    except Exception as exc:
        logger.error(
            "Error in send_class_reminders task: %s",
            exc,
            exc_info=True,
        )
    finally:
        if db is not None:
            db.close()


def start_schedule_reminder_scheduler():
    """
    Start the scheduler for sending class reminders.
    Runs every minute to check for upcoming classes.
    """
    try:
        if scheduler.running:
            logger.warning("Schedule reminder scheduler is already running")
            return

        scheduler.add_job(
            send_class_reminders,
            trigger=IntervalTrigger(minutes=1),
            id="class_reminder_job",
            name="Send class reminder emails",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )

        scheduler.start()
        logger.info(
            "Schedule reminder scheduler started successfully - will check for reminders every minute"
        )
    except Exception as exc:
        logger.error(
            "Error starting schedule reminder scheduler: %s",
            exc,
            exc_info=True,
        )


def stop_schedule_reminder_scheduler():
    """Stop the scheduler gracefully."""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("Schedule reminder scheduler stopped gracefully")
        else:
            logger.info("Schedule reminder scheduler was not running")
    except Exception as exc:
        logger.error(
            "Error stopping schedule reminder scheduler: %s",
            exc,
            exc_info=True,
        )
