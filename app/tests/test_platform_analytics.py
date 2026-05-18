"""Tests for platform analytics recording."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import DefaultBase
from app.helpers.analytics_context import classify_email_failure, map_login_failure_reason
from app.models.platform_analytics import (
    LoginAuditEvent,
    PlatformEmailEvent,
    PlatformErrorEvent,
)
from app.services.analytics_service import (
    record_login_event,
    record_platform_email_event,
)


@pytest.fixture
def analytics_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DefaultBase.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def _session_write(fn):
        db = Session()
        try:
            fn(db)
            db.commit()
        finally:
            db.close()

    monkeypatch.setattr("app.services.analytics_service._session_write", _session_write)
    monkeypatch.setattr("app.services.analytics_service.DefaultSessionLocal", Session)
    return Session


def test_map_login_failure_reason_invalid_password():
    assert map_login_failure_reason("Invalid password") == "invalid_password"
    assert map_login_failure_reason("Invalid username") == "invalid_username"


def test_classify_email_smtp_invalid_credentials():
    error_type, _ = classify_email_failure(
        "SMTP authentication failed: invalid credentials"
    )
    assert error_type == "smtp_invalid_credentials"


def test_record_login_failure_creates_audit_and_error(analytics_db):
    record_login_event(
        method="password",
        outcome="failure",
        failure_reason="invalid_password",
        failure_detail="Invalid password",
        tenant_id=1,
        tenant_name="test_school",
        identifier="user@example.com",
    )
    db = analytics_db()
    assert db.query(LoginAuditEvent).count() == 1
    assert db.query(PlatformErrorEvent).filter_by(source="login").count() == 1
    err = db.query(PlatformErrorEvent).first()
    assert err.error_type == "invalid_password"
    assert "Invalid password" in err.message
    db.close()


def test_parse_range_date_only_includes_full_day():
    from app.services.platform_analytics_queries import _parse_range

    start, end = _parse_range(
        datetime(2026, 5, 16, 0, 0, 0),
        datetime(2026, 5, 16, 0, 0, 0),
    )
    assert start.hour == 0
    assert end.hour == 23
    assert end.minute == 59


def test_record_failed_email_creates_error_with_smtp_type(analytics_db):
    record_platform_email_event(
        tenant_id=2,
        recipient_email="a@b.com",
        subject="Test",
        status="FAILED",
        failure_reason="SMTPAuthenticationError: invalid credentials",
        email_category="general",
    )
    db = analytics_db()
    assert db.query(PlatformEmailEvent).count() == 1
    err = db.query(PlatformErrorEvent).filter_by(source="email").first()
    assert err is not None
    assert err.error_type == "smtp_invalid_credentials"
    db.close()
