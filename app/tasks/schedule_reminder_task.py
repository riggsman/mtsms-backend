"""
Scheduled task for sending class reminder emails
"""
import logging
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.database.base import get_db_session
from app.services.schedule_reminder_service import ScheduleReminderService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def send_class_reminders():
    """
    Task function to send class reminder emails
    This runs every minute to check for classes starting at configured reminder times
    """
    try:
        db: Session = next(get_db_session())
        reminder_service = ScheduleReminderService(db)
        
        # Get all unique reminder times from tenant settings
        from app.models.tenant_settings import TenantSettings
        tenant_settings = db.query(TenantSettings).filter(
            TenantSettings.email_reminder_time.isnot(None)
        ).all()
        
        reminder_times = set()
        for ts in tenant_settings:
            if ts.email_reminder_time:
                reminder_times.add(ts.email_reminder_time)
        
        # If no custom settings, use default 30 minutes
        if not reminder_times:
            reminder_times = {30}
        
        # Check for each reminder time
        for minutes_ahead in reminder_times:
            try:
                asyncio.run(reminder_service.send_reminders_for_upcoming_classes(minutes_ahead=minutes_ahead))
            except Exception as e:
                logger.error(f"Error sending reminders for {minutes_ahead} minutes: {str(e)}")
        
        db.close()
    except Exception as e:
        logger.error(f"Error in send_class_reminders task: {str(e)}")


def start_schedule_reminder_scheduler():
    """
    Start the scheduler for sending class reminders
    Runs every minute to check for upcoming classes
    """
    try:
        if scheduler.running:
            logger.warning("Schedule reminder scheduler is already running")
            return
        
        # Add job to run every minute
        scheduler.add_job(
            send_class_reminders,
            trigger=IntervalTrigger(minutes=1),
            id='class_reminder_job',
            name='Send class reminder emails',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Schedule reminder scheduler started successfully - will check for reminders every minute")
    except Exception as e:
        logger.error(f"Error starting schedule reminder scheduler: {str(e)}", exc_info=True)


def stop_schedule_reminder_scheduler():
    """
    Stop the scheduler gracefully
    """
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)  # Wait for running jobs to complete
            logger.info("Schedule reminder scheduler stopped gracefully")
        else:
            logger.info("Schedule reminder scheduler was not running")
    except Exception as e:
        logger.error(f"Error stopping schedule reminder scheduler: {str(e)}", exc_info=True)
