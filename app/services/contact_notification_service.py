"""Notify platform admins when a public contact form message is submitted."""

from __future__ import annotations

import logging
from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.conf.config import settings
from app.database.base import DefaultSessionLocal
from app.helpers.system_settings_cache import get_cached_system_settings
from app.helpers.user_roles import (
    user_is_system_super_admin,
    user_system_permissions_list,
)
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

CONTACT_NOTIFICATION_PERMISSION = "contact_notifications"


def collect_contact_notification_recipients(db: Session) -> List[str]:
    """
    Resolve unique recipient emails for new contact-form alerts:
    - platform_support_email from system settings
    - all system_super_admin users with an email
    - system_admin users granted contact_notifications
    """
    emails: Set[str] = set()

    row: Optional[SystemSettings] = get_cached_system_settings()
    if row is None:
        row = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()

    if row and getattr(row, "email_notifications", True) is False:
        return []

    if row and row.platform_support_email:
        support = str(row.platform_support_email).strip()
        if support and "@" in support:
            emails.add(support.lower())

    users = (
        db.query(User)
        .filter(
            User.user_type == "SYSTEM",
            User.deleted_at.is_(None),
        )
        .all()
    )
    for user in users:
        addr = (user.email or "").strip()
        if not addr or "@" not in addr:
            continue
        if user_is_system_super_admin(user):
            emails.add(addr.lower())
            continue
        perms = user_system_permissions_list(user)
        if CONTACT_NOTIFICATION_PERMISSION in perms:
            emails.add(addr.lower())

    return sorted(emails)


def _build_admin_notification_email(
    *,
    app_name: str,
    name: str,
    email: str,
    subject: str,
    message: str,
    phone: Optional[str],
    message_id: int,
) -> tuple[str, str, str]:
    admin_subject = f"[{app_name}] New contact message: {subject}"
    phone_html = f"<p><strong>Phone:</strong> {phone}</p>" if phone else ""
    phone_text = f"Phone: {phone}\n" if phone else ""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2c3e50; color: white; padding: 16px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            .details {{ background-color: #fff; padding: 15px; border-left: 4px solid #3498db; margin-top: 16px; }}
            .footer {{ text-align: center; padding: 16px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>New contact form submission</h1>
            </div>
            <div class="content">
                <p>A visitor submitted the public contact form on {app_name}.</p>
                <div class="details">
                    <p><strong>Message ID:</strong> #{message_id}</p>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
                    {phone_html}
                    <p><strong>Subject:</strong> {subject}</p>
                    <p><strong>Message:</strong></p>
                    <p>{message}</p>
                </div>
                <p>Review and reply from the admin dashboard under Contact Messages.</p>
            </div>
            <div class="footer">
                <p>Automated notification from {app_name}.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
New contact form submission on {app_name}

Message ID: #{message_id}
Name: {name}
Email: {email}
{phone_text}Subject: {subject}

Message:
{message}

Review and reply from the admin dashboard under Contact Messages.
""".strip()

    return admin_subject, html_content, text_content


async def send_contact_admin_notifications(
    *,
    message_id: int,
    name: str,
    email: str,
    subject: str,
    message: str,
    phone: Optional[str] = None,
) -> None:
    """Send alert emails to all configured platform recipients."""
    db = DefaultSessionLocal()
    try:
        recipients = collect_contact_notification_recipients(db)
    finally:
        db.close()

    if not recipients:
        logger.warning(
            "Contact form message #%s stored but no notification recipients are configured",
            message_id,
        )
        return

    app_name = getattr(settings, "APP_NAME", "EduSphere")
    admin_subject, html_content, text_content = _build_admin_notification_email(
        app_name=app_name,
        name=name,
        email=email,
        subject=subject,
        message=message,
        phone=phone,
        message_id=message_id,
    )

    for to_email in recipients:
        try:
            await EmailService.send_email(
                to_email=to_email,
                subject=admin_subject,
                html_content=html_content,
                text_content=text_content,
            )
        except Exception:
            logger.exception("Failed to send contact notification to %s", to_email)
