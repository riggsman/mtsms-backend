"""Best-effort platform analytics writers (shared DB)."""

from __future__ import annotations

import logging
from typing import Optional

from app.database.base import DefaultSessionLocal
from app.helpers.analytics_context import classify_email_failure
from app.models.platform_analytics import (
    ApiRequestLog,
    LoginAuditEvent,
    OtpAuditEvent,
    PlatformEmailEvent,
    PlatformErrorEvent,
)

logger = logging.getLogger(__name__)


def _session_write(fn) -> None:
    db = DefaultSessionLocal()
    try:
        fn(db)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Analytics write failed: %s", exc, exc_info=True)
    finally:
        db.close()


def record_platform_error(
    *,
    source: str,
    message: str,
    error_type: Optional[str] = None,
    tenant_id: Optional[int] = None,
    tenant_name: Optional[str] = None,
    user_id: Optional[int] = None,
    status_code: Optional[int] = None,
    method: Optional[str] = None,
    path: Optional[str] = None,
    route_template: Optional[str] = None,
) -> None:
    safe_message = (message or "Unknown error")[:2000]

    def _write(db):
        db.add(
            PlatformErrorEvent(
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                user_id=user_id,
                source=source,
                error_type=error_type,
                message=safe_message,
                status_code=status_code,
                method=method,
                path=(path or "")[:512] or None,
                route_template=(route_template or path or "")[:512] or None,
            )
        )

    _session_write(_write)


def record_login_event(
    *,
    method: str,
    outcome: str,
    failure_reason: Optional[str] = None,
    failure_detail: Optional[str] = None,
    tenant_id: Optional[int] = None,
    tenant_name: Optional[str] = None,
    user_id: Optional[int] = None,
    identifier: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    detail_message = (failure_detail or failure_reason or "Login failed")[:2000]

    def _write(db):
        db.add(
            LoginAuditEvent(
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                user_id=user_id,
                identifier=(identifier or "")[:255] or None,
                method=method,
                outcome=outcome,
                failure_reason=failure_reason,
                failure_detail=failure_detail,
                ip_address=ip_address,
                user_agent=(user_agent or "")[:512] or None,
            )
        )
        if outcome == "failure":
            db.add(
                PlatformErrorEvent(
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    user_id=user_id,
                    source="login",
                    error_type=failure_reason or "login_failure",
                    message=detail_message,
                    method=method,
                )
            )

    _session_write(_write)


def record_otp_event(
    *,
    event_type: str,
    tenant_id: Optional[int] = None,
    tenant_name: Optional[str] = None,
    user_id: Optional[int] = None,
    message: Optional[str] = None,
) -> None:
    def _write(db):
        db.add(
            OtpAuditEvent(
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                user_id=user_id,
                event_type=event_type,
            )
        )
        if event_type in ("verify_failed", "request_no_user"):
            db.add(
                PlatformErrorEvent(
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    user_id=user_id,
                    source="otp",
                    error_type=event_type,
                    message=(message or f"OTP event: {event_type}")[:2000],
                )
            )

    _session_write(_write)


def record_platform_email_event(
    *,
    tenant_id: Optional[int],
    recipient_email: str,
    subject: Optional[str],
    status: str,
    failure_reason: Optional[str] = None,
    email_category: Optional[str] = "general",
) -> None:
    def _write(db):
        db.add(
            PlatformEmailEvent(
                tenant_id=tenant_id,
                recipient_email=recipient_email,
                subject=subject,
                status=status,
                failure_reason=failure_reason,
                email_category=email_category,
            )
        )
        if status in ("FAILED", "BOUNCED"):
            error_type, classified = classify_email_failure(failure_reason)
            detail = classified
            if recipient_email and recipient_email not in detail:
                detail = f"{detail} (to {recipient_email})"
            if subject and subject not in detail:
                detail = f"[{subject}] {detail}"
            db.add(
                PlatformErrorEvent(
                    tenant_id=tenant_id,
                    source="email",
                    error_type=error_type,
                    message=detail[:2000],
                )
            )

    _session_write(_write)


def record_api_request(
    *,
    tenant_id: Optional[int],
    tenant_name: Optional[str],
    user_id: Optional[int],
    method: str,
    path: str,
    route_template: Optional[str],
    status_code: int,
    duration_ms: Optional[int],
    billing_category: str = "api",
) -> None:
    def _write(db):
        db.add(
            ApiRequestLog(
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                user_id=user_id,
                method=method,
                path=path[:512],
                route_template=(route_template or path)[:512],
                status_code=status_code,
                duration_ms=duration_ms,
                billing_category=billing_category,
            )
        )

    _session_write(_write)
