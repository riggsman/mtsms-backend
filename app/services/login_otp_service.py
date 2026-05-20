"""Passwordless login via email OTP (10-minute TTL, single use)."""

import logging
import secrets
import string
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.authentication.authenticator import hash_password, verify_password
from app.apis.login import build_login_response
from app.conf.config import settings
from app.database.sessionManager import create_standalone_db_session
from app.helpers.async_helper import run_async_safe
from app.models.login_email_otp import LoginEmailOtp
from app.models.user import User
from app.schemas.login import LoginOtpRequestResponse, LoginResponse
from app.helpers.analytics_context import tenant_id_and_name
from app.services.analytics_service import record_login_event, record_otp_event

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = 10
OTP_GENERIC_SENT_MESSAGE = (
    "If an account with that email exists, a sign-in code has been sent. "
    "Check your inbox (valid for 10 minutes)."
)


def _generate_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _find_user_by_email(db: Session, email: str) -> User | None:
    normalized = _normalize_email(email)
    if not normalized:
        return None
    return (
        db.query(User)
        .filter(func.lower(User.email) == normalized, User.deleted_at.is_(None))
        .first()
    )


async def request_login_otp(
    db: Session,
    email: str,
    tenant_name: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> LoginOtpRequestResponse:
    user = _find_user_by_email(db, email)
    tid, tname = tenant_id_and_name(tenant_name=tenant_name, user=user)
    if not user or user.is_active != "active":
        record_otp_event(
            event_type="request_no_user",
            tenant_id=tid,
            tenant_name=tname,
        )
        return LoginOtpRequestResponse(message=OTP_GENERIC_SENT_MESSAGE)

    from app.dependencies.tenant_activation import raise_if_tenant_suspended_for_login

    try:
        raise_if_tenant_suspended_for_login(db, user)
    except HTTPException:
        return LoginOtpRequestResponse(message=OTP_GENERIC_SENT_MESSAGE)

    otp_plain = _generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)

    db.query(LoginEmailOtp).filter(
        LoginEmailOtp.user_id == user.id,
        LoginEmailOtp.used_at.is_(None),
    ).update({LoginEmailOtp.used_at: datetime.utcnow()}, synchronize_session=False)

    record = LoginEmailOtp(
        user_id=user.id,
        code_hash=hash_password(otp_plain),
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()

    tid, tname = tenant_id_and_name(tenant_name=tenant_name, user=user)
    record_otp_event(
        event_type="generated",
        tenant_id=tid,
        tenant_name=tname,
        user_id=user.id,
    )

    institution_id = user.institution_id
    recipient = user.email
    display_name = f"{user.firstname} {user.lastname}".strip() or user.username

    email_subject = "Your sign-in code"
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">Sign in to {settings.APP_NAME}</h2>
            <p>Hello {display_name},</p>
            <p>Use this one-time code to sign in without a password:</p>
            <div style="background-color: #f8f9fa; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0;">
                <h1 style="color: #667eea; margin: 0; font-size: 32px; letter-spacing: 5px;">{otp_plain}</h1>
            </div>
            <p><strong>This code expires in {OTP_TTL_MINUTES} minutes.</strong></p>
            <p style="color: #dc3545;">If you did not request this code, you can ignore this email.</p>
        </div>
    </body>
    </html>
    """
    text_content = f"""
Hello {display_name},

Use this one-time code to sign in to {settings.APP_NAME}:

{otp_plain}

This code expires in {OTP_TTL_MINUTES} minutes.

If you did not request this code, you can ignore this email.
    """

    async def _send_email():
        from app.services.email_tracker import EmailTracker

        db_email = create_standalone_db_session(tenant_name)
        try:
            await EmailTracker.send_with_tracking(
                db=db_email,
                sender_email=settings.SMTP_FROM_EMAIL,
                recipient_email=recipient,
                subject=email_subject,
                html_content=html_content,
                text_content=text_content,
                institution_id=institution_id,
                email_category="login_otp",
            )
        except Exception as exc:
            logger.error("Error sending login OTP email: %s", exc)
            from app.services.analytics_service import record_platform_email_event

            record_platform_email_event(
                tenant_id=institution_id,
                recipient_email=recipient,
                subject=email_subject,
                status="FAILED",
                failure_reason=str(exc),
                email_category="login_otp",
            )
        finally:
            db_email.close()

    run_async_safe(_send_email())
    return LoginOtpRequestResponse(message=OTP_GENERIC_SENT_MESSAGE)


async def verify_login_otp(
    db: Session,
    email: str,
    otp: str,
    tenant_name: str | None = None,
) -> LoginResponse:
    code = (otp or "").strip()
    if not code or len(code) != 6 or not code.isdigit():
        tid, tname = tenant_id_and_name(tenant_name=tenant_name)
        record_otp_event(
            event_type="verify_failed",
            tenant_id=tid,
            tenant_name=tname,
            message="Invalid OTP format",
        )
        record_login_event(
            method="otp_verify",
            outcome="failure",
            failure_reason="invalid_otp",
            failure_detail="Invalid or expired sign-in code",
            tenant_id=tid,
            tenant_name=tname,
            identifier=email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired sign-in code",
        )

    user = _find_user_by_email(db, email)
    tid, tname = tenant_id_and_name(tenant_name=tenant_name, user=user)
    if not user or user.is_active != "active":
        record_otp_event(
            event_type="verify_failed",
            tenant_id=tid,
            tenant_name=tname,
            message="Invalid or expired sign-in code",
        )
        record_login_event(
            method="otp_verify",
            outcome="failure",
            failure_reason="invalid_otp",
            failure_detail="Invalid or expired sign-in code",
            tenant_id=tid,
            tenant_name=tname,
            identifier=email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired sign-in code",
        )

    now = datetime.utcnow()
    record = (
        db.query(LoginEmailOtp)
        .filter(
            LoginEmailOtp.user_id == user.id,
            LoginEmailOtp.used_at.is_(None),
            LoginEmailOtp.expires_at > now,
        )
        .order_by(LoginEmailOtp.created_at.desc())
        .first()
    )

    if not record or not verify_password(code, record.code_hash):
        record_otp_event(
            event_type="verify_failed",
            tenant_id=tid,
            tenant_name=tname,
            user_id=user.id,
            message="Invalid or expired sign-in code",
        )
        record_login_event(
            method="otp_verify",
            outcome="failure",
            failure_reason="invalid_otp",
            failure_detail="Invalid or expired sign-in code",
            tenant_id=tid,
            tenant_name=tname,
            user_id=user.id,
            identifier=email,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired sign-in code",
        )

    record.used_at = now
    db.commit()

    from app.dependencies.tenant_activation import raise_if_tenant_suspended_for_login

    raise_if_tenant_suspended_for_login(db, user)

    record_otp_event(
        event_type="verified",
        tenant_id=tid,
        tenant_name=tname,
        user_id=user.id,
    )

    return build_login_response(user, tenant_name)
