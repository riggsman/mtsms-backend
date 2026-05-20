"""Read-side aggregations for platform analytics APIs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.platform_analytics import (
    ApiRequestLog,
    LoginAuditEvent,
    OtpAuditEvent,
    PlatformEmailEvent,
    PlatformErrorEvent,
)
from app.helpers.analytics_context import classify_email_failure
from app.models.tenant import Tenant


def _parse_range(
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> tuple[datetime, datetime]:
    """Inclusive UTC range. Date-only `to_date` values include the full calendar day."""
    now = datetime.utcnow()
    if from_date is None and to_date is None:
        return datetime(2020, 1, 1), now

    end = to_date or now
    if to_date is not None and (
        to_date.hour == 0
        and to_date.minute == 0
        and to_date.second == 0
        and to_date.microsecond == 0
    ):
        end = to_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    start = from_date or (end - timedelta(days=30))
    if from_date is not None and (
        from_date.hour == 0
        and from_date.minute == 0
        and from_date.second == 0
        and from_date.microsecond == 0
    ):
        start = from_date.replace(hour=0, minute=0, second=0, microsecond=0)

    return start, end


def _tenant_filter(query, model, tenant_id: Optional[int]):
    if tenant_id is not None:
        return query.filter(model.tenant_id == tenant_id)
    return query


def get_summary(
    db: Session,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    tenant_id: Optional[int] = None,
) -> dict[str, Any]:
    start, end = _parse_range(from_date, to_date)

    def _login_base():
        q = db.query(LoginAuditEvent).filter(
            LoginAuditEvent.created_at >= start,
            LoginAuditEvent.created_at <= end,
        )
        return _tenant_filter(q, LoginAuditEvent, tenant_id)

    login_failures = _login_base().filter(LoginAuditEvent.outcome == "failure").count()
    login_success = _login_base().filter(LoginAuditEvent.outcome == "success").count()

    def _otp_base():
        q = db.query(OtpAuditEvent).filter(
            OtpAuditEvent.created_at >= start,
            OtpAuditEvent.created_at <= end,
        )
        return _tenant_filter(q, OtpAuditEvent, tenant_id)

    otp_generated = _otp_base().filter(OtpAuditEvent.event_type == "generated").count()
    otp_verified = _otp_base().filter(OtpAuditEvent.event_type == "verified").count()
    otp_failed = _otp_base().filter(OtpAuditEvent.event_type == "verify_failed").count()

    email_q = db.query(PlatformEmailEvent).filter(
        PlatformEmailEvent.created_at >= start,
        PlatformEmailEvent.created_at <= end,
    )
    email_q = _tenant_filter(email_q, PlatformEmailEvent, tenant_id)

    emails_total = email_q.count()
    emails_sent = email_q.filter(
        PlatformEmailEvent.status.in_(("SENT", "DELIVERED"))
    ).count()
    emails_failed = email_q.filter(
        PlatformEmailEvent.status.in_(("FAILED", "BOUNCED"))
    ).count()

    req_q = db.query(ApiRequestLog).filter(
        ApiRequestLog.created_at >= start,
        ApiRequestLog.created_at <= end,
    )
    req_q = _tenant_filter(req_q, ApiRequestLog, tenant_id)

    api_requests = req_q.count()
    api_errors = req_q.filter(ApiRequestLog.status_code >= 400).count()

    err_q = db.query(PlatformErrorEvent).filter(
        PlatformErrorEvent.created_at >= start,
        PlatformErrorEvent.created_at <= end,
    )
    err_q = _tenant_filter(err_q, PlatformErrorEvent, tenant_id)
    total_errors = err_q.count()

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "loginFailures": login_failures,
        "loginSuccess": login_success,
        "otpGenerated": otp_generated,
        "otpVerified": otp_verified,
        "otpVerifyFailed": otp_failed,
        "emailsTotal": emails_total,
        "emailsSent": emails_sent,
        "emailsFailed": emails_failed,
        "apiRequests": api_requests,
        "apiErrors": api_errors,
        "totalErrors": total_errors,
    }


def get_platform_errors(
    db: Session,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    tenant_id: Optional[int],
    page: int,
    page_size: int,
    source: Optional[str] = None,
) -> dict[str, Any]:
    start, end = _parse_range(from_date, to_date)
    base = db.query(PlatformErrorEvent).filter(
        PlatformErrorEvent.created_at >= start,
        PlatformErrorEvent.created_at <= end,
    )
    base = _tenant_filter(base, PlatformErrorEvent, tenant_id)
    if source:
        base = base.filter(PlatformErrorEvent.source == source)

    total = base.count()
    items = (
        base.order_by(PlatformErrorEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    by_source = (
        db.query(PlatformErrorEvent.source, func.count(PlatformErrorEvent.id))
        .filter(
            PlatformErrorEvent.created_at >= start,
            PlatformErrorEvent.created_at <= end,
        )
    )
    if tenant_id is not None:
        by_source = by_source.filter(PlatformErrorEvent.tenant_id == tenant_id)
    by_source = by_source.group_by(PlatformErrorEvent.source).all()

    by_type = (
        db.query(PlatformErrorEvent.error_type, func.count(PlatformErrorEvent.id))
        .filter(
            PlatformErrorEvent.created_at >= start,
            PlatformErrorEvent.created_at <= end,
        )
    )
    if tenant_id is not None:
        by_type = by_type.filter(PlatformErrorEvent.tenant_id == tenant_id)
    by_type = by_type.group_by(PlatformErrorEvent.error_type).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "bySource": [{"source": s, "count": c} for s, c in by_source],
        "byType": [{"errorType": t or "unknown", "count": c} for t, c in by_type],
        "items": [
            {
                "id": e.id,
                "tenantId": e.tenant_id,
                "tenantName": e.tenant_name,
                "source": e.source,
                "errorType": e.error_type,
                "message": e.message,
                "statusCode": e.status_code,
                "method": e.method,
                "path": e.path,
                "routeTemplate": e.route_template,
                "createdAt": e.created_at.isoformat() if e.created_at else None,
            }
            for e in items
        ],
    }


def get_login_failures(
    db: Session,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    tenant_id: Optional[int],
    page: int,
    page_size: int,
) -> dict[str, Any]:
    start, end = _parse_range(from_date, to_date)
    base = db.query(LoginAuditEvent).filter(
        LoginAuditEvent.outcome == "failure",
        LoginAuditEvent.created_at >= start,
        LoginAuditEvent.created_at <= end,
    )
    base = _tenant_filter(base, LoginAuditEvent, tenant_id)

    total = base.count()
    items = (
        base.order_by(LoginAuditEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    reason_rows = (
        db.query(
            LoginAuditEvent.failure_reason,
            func.count(LoginAuditEvent.id),
        )
        .filter(
            LoginAuditEvent.outcome == "failure",
            LoginAuditEvent.created_at >= start,
            LoginAuditEvent.created_at <= end,
        )
    )
    if tenant_id is not None:
        reason_rows = reason_rows.filter(LoginAuditEvent.tenant_id == tenant_id)
    reason_rows = reason_rows.group_by(LoginAuditEvent.failure_reason).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "reasons": [
            {
                "reason": r or "unknown",
                "count": c,
                "label": (r or "unknown").replace("_", " "),
            }
            for r, c in reason_rows
        ],
        "items": [
            {
                "id": e.id,
                "tenantId": e.tenant_id,
                "tenantName": e.tenant_name,
                "identifier": e.identifier,
                "method": e.method,
                "failureReason": e.failure_reason,
                "failureDetail": e.failure_detail,
                "message": e.failure_detail or e.failure_reason or "Login failed",
                "createdAt": e.created_at.isoformat() if e.created_at else None,
            }
            for e in items
        ],
    }


def get_email_analytics(
    db: Session,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    tenant_id: Optional[int],
) -> dict[str, Any]:
    start, end = _parse_range(from_date, to_date)
    email_base = db.query(PlatformEmailEvent).filter(
        PlatformEmailEvent.created_at >= start,
        PlatformEmailEvent.created_at <= end,
    )
    email_base = _tenant_filter(email_base, PlatformEmailEvent, tenant_id)

    status_rows = (
        email_base.with_entities(
            PlatformEmailEvent.status, func.count(PlatformEmailEvent.id)
        )
        .group_by(PlatformEmailEvent.status)
        .all()
    )

    by_tenant = (
        db.query(
            PlatformEmailEvent.tenant_id,
            func.count(PlatformEmailEvent.id),
            func.sum(
                func.IF(
                    PlatformEmailEvent.status.in_(("SENT", "DELIVERED")),
                    1,
                    0,
                )
            ),
            func.sum(
                func.IF(
                    PlatformEmailEvent.status.in_(("FAILED", "BOUNCED")),
                    1,
                    0,
                )
            ),
        )
        .filter(
            PlatformEmailEvent.created_at >= start,
            PlatformEmailEvent.created_at <= end,
        )
    )
    if tenant_id is not None:
        by_tenant = by_tenant.filter(PlatformEmailEvent.tenant_id == tenant_id)
    by_tenant = by_tenant.group_by(PlatformEmailEvent.tenant_id).all()

    tenant_names = {
        t.id: t.name for t in db.query(Tenant.id, Tenant.name).all()
    }

    failure_rows = (
        db.query(
            PlatformEmailEvent.failure_reason,
            func.count(PlatformEmailEvent.id),
        )
        .filter(
            PlatformEmailEvent.created_at >= start,
            PlatformEmailEvent.created_at <= end,
            PlatformEmailEvent.status.in_(("FAILED", "BOUNCED")),
        )
    )
    if tenant_id is not None:
        failure_rows = failure_rows.filter(PlatformEmailEvent.tenant_id == tenant_id)
    failure_rows = failure_rows.group_by(PlatformEmailEvent.failure_reason).all()

    credential_failures = 0
    for reason, count in failure_rows:
        error_type, _ = classify_email_failure(reason)
        if error_type == "smtp_invalid_credentials":
            credential_failures += count

    smtp_error_rows = (
        db.query(PlatformErrorEvent)
        .filter(
            PlatformErrorEvent.source == "email",
            PlatformErrorEvent.error_type == "smtp_invalid_credentials",
            PlatformErrorEvent.created_at >= start,
            PlatformErrorEvent.created_at <= end,
        )
    )
    if tenant_id is not None:
        smtp_error_rows = smtp_error_rows.filter(PlatformErrorEvent.tenant_id == tenant_id)
    smtp_credential_events = smtp_error_rows.count()

    return {
        "smtpCredentialFailures": max(credential_failures, smtp_credential_events),
        "byStatus": [{"status": s, "count": c} for s, c in status_rows],
        "byTenant": [
            {
                "tenantId": tid,
                "tenantName": tenant_names.get(tid, "Unknown"),
                "total": total,
                "sent": int(sent or 0),
                "failed": int(failed or 0),
            }
            for tid, total, sent, failed in by_tenant
        ],
        "failureReasons": [
            {"reason": (r or "unknown")[:200], "count": c} for r, c in failure_rows
        ],
    }


def get_otp_analytics(
    db: Session,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    tenant_id: Optional[int],
) -> dict[str, Any]:
    start, end = _parse_range(from_date, to_date)
    base = db.query(OtpAuditEvent).filter(
        OtpAuditEvent.created_at >= start,
        OtpAuditEvent.created_at <= end,
    )
    base = _tenant_filter(base, OtpAuditEvent, tenant_id)

    rows = (
        base.with_entities(OtpAuditEvent.event_type, func.count(OtpAuditEvent.id))
        .group_by(OtpAuditEvent.event_type)
        .all()
    )
    return {"byEvent": [{"eventType": e, "count": c} for e, c in rows]}


def get_request_analytics(
    db: Session,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    tenant_id: Optional[int],
) -> dict[str, Any]:
    start, end = _parse_range(from_date, to_date)
    def _req_base():
        q = db.query(ApiRequestLog).filter(
            ApiRequestLog.created_at >= start,
            ApiRequestLog.created_at <= end,
        )
        return _tenant_filter(q, ApiRequestLog, tenant_id)

    by_tenant = (
        db.query(
            ApiRequestLog.tenant_id,
            ApiRequestLog.tenant_name,
            func.count(ApiRequestLog.id),
            func.sum(func.IF(ApiRequestLog.status_code >= 400, 1, 0)),
        )
        .filter(
            ApiRequestLog.created_at >= start,
            ApiRequestLog.created_at <= end,
        )
    )
    if tenant_id is not None:
        by_tenant = by_tenant.filter(ApiRequestLog.tenant_id == tenant_id)
    by_tenant = by_tenant.group_by(ApiRequestLog.tenant_id, ApiRequestLog.tenant_name).all()

    top_routes = (
        _req_base()
        .with_entities(
            ApiRequestLog.route_template,
            func.count(ApiRequestLog.id),
        )
        .group_by(ApiRequestLog.route_template)
        .order_by(func.count(ApiRequestLog.id).desc())
        .limit(20)
        .all()
    )

    error_base = _req_base().filter(ApiRequestLog.status_code >= 400)

    top_error_routes = (
        error_base.with_entities(
            ApiRequestLog.route_template,
            ApiRequestLog.status_code,
            func.count(ApiRequestLog.id),
        )
        .group_by(ApiRequestLog.route_template, ApiRequestLog.status_code)
        .order_by(func.count(ApiRequestLog.id).desc())
        .limit(20)
        .all()
    )

    status_breakdown = (
        error_base.with_entities(
            ApiRequestLog.status_code,
            func.count(ApiRequestLog.id),
        )
        .group_by(ApiRequestLog.status_code)
        .order_by(func.count(ApiRequestLog.id).desc())
        .all()
    )

    error_logs = (
        error_base.order_by(ApiRequestLog.created_at.desc()).limit(100).all()
    )

    recent_errors = []
    for log in error_logs:
        detail = (
            db.query(PlatformErrorEvent)
            .filter(
                PlatformErrorEvent.created_at >= log.created_at - timedelta(seconds=5),
                PlatformErrorEvent.created_at <= log.created_at + timedelta(seconds=5),
                PlatformErrorEvent.source.in_(("api", "login")),
            )
            .filter(
                or_(
                    PlatformErrorEvent.path == log.path,
                    PlatformErrorEvent.route_template == log.route_template,
                )
            )
            .order_by(PlatformErrorEvent.id.desc())
            .first()
        )
        recent_errors.append(
            {
                "id": log.id,
                "tenantId": log.tenant_id,
                "tenantName": log.tenant_name or "Platform",
                "method": log.method,
                "route": log.route_template or log.path,
                "path": log.path,
                "statusCode": log.status_code,
                "durationMs": log.duration_ms,
                "message": detail.message if detail else f"HTTP {log.status_code}",
                "errorType": detail.error_type if detail else None,
                "createdAt": log.created_at.isoformat() if log.created_at else None,
            }
        )

    total_api_errors = error_base.count()

    return {
        "totalErrors": total_api_errors,
        "errorsByStatus": [
            {"statusCode": code, "count": cnt} for code, cnt in status_breakdown
        ],
        "topErrorRoutes": [
            {
                "route": route or "unknown",
                "statusCode": status,
                "count": cnt,
            }
            for route, status, cnt in top_error_routes
        ],
        "recentErrors": recent_errors,
        "byTenant": [
            {
                "tenantId": tid,
                "tenantName": tname or "Platform",
                "requests": cnt,
                "errors": int(err or 0),
            }
            for tid, tname, cnt, err in by_tenant
        ],
        "topRoutes": [{"route": r, "count": c} for r, c in top_routes],
    }


def get_tenants_matrix(
    db: Session,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> dict[str, Any]:
    start, end = _parse_range(from_date, to_date)
    tenants = db.query(Tenant).all()
    rows = []

    for tenant in tenants:
        tid = tenant.id
        login_failures = (
            db.query(LoginAuditEvent)
            .filter(
                LoginAuditEvent.tenant_id == tid,
                LoginAuditEvent.outcome == "failure",
                LoginAuditEvent.created_at >= start,
                LoginAuditEvent.created_at <= end,
            )
            .count()
        )
        emails_sent = (
            db.query(PlatformEmailEvent)
            .filter(
                PlatformEmailEvent.tenant_id == tid,
                PlatformEmailEvent.status.in_(("SENT", "DELIVERED")),
                PlatformEmailEvent.created_at >= start,
                PlatformEmailEvent.created_at <= end,
            )
            .count()
        )
        emails_failed = (
            db.query(PlatformEmailEvent)
            .filter(
                PlatformEmailEvent.tenant_id == tid,
                PlatformEmailEvent.status.in_(("FAILED", "BOUNCED")),
                PlatformEmailEvent.created_at >= start,
                PlatformEmailEvent.created_at <= end,
            )
            .count()
        )
        api_requests = (
            db.query(ApiRequestLog)
            .filter(
                ApiRequestLog.tenant_id == tid,
                ApiRequestLog.created_at >= start,
                ApiRequestLog.created_at <= end,
            )
            .count()
        )
        otp_generated = (
            db.query(OtpAuditEvent)
            .filter(
                OtpAuditEvent.tenant_id == tid,
                OtpAuditEvent.event_type == "generated",
                OtpAuditEvent.created_at >= start,
                OtpAuditEvent.created_at <= end,
            )
            .count()
        )

        rows.append(
            {
                "tenantId": tid,
                "tenantName": tenant.name,
                "loginFailures": login_failures,
                "emailsSent": emails_sent,
                "emailsFailed": emails_failed,
                "apiRequests": api_requests,
                "otpGenerated": otp_generated,
            }
        )

    return {"tenants": rows}


def _calc_series_trend(series: list[dict], value_key: str, recent_size: int = 3) -> tuple[str, float]:
    """Return trend direction (up/down/stable) and percent change for recent vs older buckets."""
    if len(series) < 2:
        return "stable", 0.0
    recent = series[-recent_size:]
    older = series[: -recent_size] if len(series) > recent_size else series[:1]
    recent_avg = sum(item.get(value_key, 0) or 0 for item in recent) / len(recent)
    older_avg = sum(item.get(value_key, 0) or 0 for item in older) / len(older)
    if recent_avg > older_avg:
        trend = "up"
    elif recent_avg < older_avg:
        trend = "down"
    else:
        trend = "stable"
    change = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0.0
    return trend, round(change, 1)


def get_tenant_growth_series(
    db: Session,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """New tenants per calendar month in the requested range (default: last 12 months)."""
    from dateutil.relativedelta import relativedelta

    now = datetime.utcnow()
    if from_date is None and to_date is None:
        range_end = now
        range_start = (now.replace(day=1) - relativedelta(months=11)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        range_start, range_end = _parse_range(from_date, to_date)

    cursor = range_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_month = range_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    series: list[dict[str, Any]] = []
    while cursor <= end_month:
        month_end = cursor + relativedelta(months=1)
        count = (
            db.query(Tenant)
            .filter(Tenant.created_at >= cursor, Tenant.created_at < month_end)
            .count()
        )
        series.append(
            {
                "month": cursor.strftime("%b %Y"),
                "monthShort": cursor.strftime("%b"),
                "date": cursor.strftime("%Y-%m-%d"),
                "tenants": count,
            }
        )
        cursor = month_end

    cumulative = 0
    for item in series:
        cumulative += item["tenants"]
        item["cumulative"] = cumulative
    return series


def get_user_activity_series(
    db: Session,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Successful logins per day (login_audit_events) in the requested range (default: last 30 days)."""
    now = datetime.utcnow()
    if from_date is None and to_date is None:
        range_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        range_start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        range_start, range_end = _parse_range(from_date, to_date)

    series: list[dict[str, Any]] = []
    cursor = range_start.replace(hour=0, minute=0, second=0, microsecond=0)
    while cursor <= range_end:
        day_end = cursor + timedelta(days=1)
        active = (
            db.query(LoginAuditEvent)
            .filter(
                LoginAuditEvent.outcome == "success",
                LoginAuditEvent.created_at >= cursor,
                LoginAuditEvent.created_at < day_end,
            )
            .count()
        )
        series.append(
            {
                "date": cursor.strftime("%Y-%m-%d"),
                "day": cursor.strftime("%a"),
                "activeUsers": active,
                "newUsers": active,
            }
        )
        cursor = day_end
        if len(series) > 366:
            break

    cumulative = 0
    for item in series:
        cumulative += item["activeUsers"]
        item["cumulative"] = cumulative
    return series
