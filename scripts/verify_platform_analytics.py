#!/usr/bin/env python3
"""Standalone verification for platform analytics (no pytest required)."""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import DefaultBase
from app.helpers.analytics_context import classify_email_failure, map_login_failure_reason
from app.services.analytics_service import record_login_event, record_platform_email_event
from app.models.platform_analytics import ApiRequestLog
from app.services.platform_analytics_queries import (
    _parse_range,
    get_login_failures,
    get_platform_errors,
    get_request_analytics,
)


def main() -> int:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DefaultBase.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    import app.services.analytics_service as svc

    def _session_write(fn):
        db = Session()
        try:
            fn(db)
            db.commit()
        finally:
            db.close()

    svc._session_write = _session_write
    svc.DefaultSessionLocal = Session

    assert map_login_failure_reason("Invalid password") == "invalid_password"
    assert map_login_failure_reason("Invalid username") == "invalid_username"

    et, _ = classify_email_failure("535 Authentication failed: invalid credentials")
    assert et == "smtp_invalid_credentials"

    start, end = _parse_range(
        datetime(2026, 5, 16, 0, 0, 0),
        datetime(2026, 5, 16, 0, 0, 0),
    )
    assert end.hour == 23

    record_login_event(
        method="password",
        outcome="failure",
        failure_reason="invalid_password",
        failure_detail="Invalid password",
        tenant_id=1,
        tenant_name="demo_school",
        identifier="admin@demo.com",
    )

    def _add_api_error(status_code: int, path: str, route: str):
        def _w(db):
            db.add(
                ApiRequestLog(
                    tenant_id=1,
                    tenant_name="demo_school",
                    method="GET",
                    path=path,
                    route_template=route,
                    status_code=status_code,
                    duration_ms=120,
                )
            )
        _session_write(_w)

    _add_api_error(403, "/api/v1/system/analytics/platform/summary", "/api/v1/system/analytics/platform/summary")
    _add_api_error(401, "/api/v1/students", "/api/v1/students/{id}")
    _add_api_error(404, "/api/v1/unknown", "/api/v1/unknown")

    record_platform_email_event(
        tenant_id=1,
        recipient_email="user@test.com",
        subject="Welcome",
        status="FAILED",
        failure_reason="SMTPAuthenticationError: invalid credentials",
        email_category="general",
    )

    db = Session()
    failures = get_login_failures(db, None, None, None, 1, 50)
    errors = get_platform_errors(db, None, None, None, 1, 50)
    requests = get_request_analytics(db, None, None, None)
    db.close()

    assert failures["total"] == 1, failures
    assert requests["totalErrors"] == 3, requests
    assert len(requests["recentErrors"]) == 3, requests
    assert failures["items"][0]["failureReason"] == "invalid_password"
    assert failures["items"][0]["message"] == "Invalid password"

    assert errors["total"] >= 2, errors
    login_err = [i for i in errors["items"] if i["source"] == "login"]
    email_err = [i for i in errors["items"] if i["source"] == "email"]
    assert len(login_err) == 1
    assert len(email_err) == 1
    assert email_err[0]["errorType"] == "smtp_invalid_credentials"

    print("OK: login failures, API HTTP errors, and SMTP email errors recorded and queryable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
