"""Tests for database pool configuration and related helpers."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.conf.config import settings
from app.database.base import DefaultBase
from app.database.engine_config import get_engine_kwargs
from app.helpers.tenant_activation_cache import (
    get_tenant_access_status,
    invalidate_tenant_access_cache,
    set_tenant_access_status,
)
from app.services.platform_analytics_queries import get_tenants_matrix


def test_engine_kwargs_defaults():
    kwargs = get_engine_kwargs()
    assert kwargs["pool_size"] == settings.DB_POOL_SIZE
    assert kwargs["max_overflow"] == settings.DB_MAX_OVERFLOW
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["pool_recycle"] == settings.DB_POOL_RECYCLE


def test_tenant_engine_kwargs_smaller_pool():
    kwargs = get_engine_kwargs(for_tenant=True)
    assert kwargs["pool_size"] == settings.TENANT_DB_POOL_SIZE
    assert kwargs["max_overflow"] == settings.TENANT_DB_MAX_OVERFLOW
    assert kwargs["pool_size"] <= settings.DB_POOL_SIZE


def test_tenant_activation_cache_roundtrip():
    invalidate_tenant_access_cache()
    assert get_tenant_access_status(99) is None
    set_tenant_access_status(99, is_suspended=False, is_activated=True)
    assert get_tenant_access_status(99) == (False, True)
    invalidate_tenant_access_cache(99)
    assert get_tenant_access_status(99) is None


@pytest.fixture
def analytics_matrix_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    DefaultBase.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        DefaultBase.metadata.drop_all(bind=engine)


def test_get_tenants_matrix_aggregates(analytics_matrix_db):
    from datetime import datetime

    from app.models.platform_analytics import ApiRequestLog, LoginAuditEvent
    from app.models.tenant import Tenant

    db = analytics_matrix_db
    t1 = Tenant(name="school_a", domain="school-a.test", category="school", is_active=True)
    t2 = Tenant(name="school_b", domain="school-b.test", category="school", is_active=True)
    db.add_all([t1, t2])
    db.commit()
    db.refresh(t1)
    db.refresh(t2)

    now = datetime.utcnow()
    db.add(
        LoginAuditEvent(
            tenant_id=t1.id,
            method="password",
            outcome="failure",
            created_at=now,
        )
    )
    db.add(
        ApiRequestLog(
            tenant_id=t2.id,
            method="GET",
            path="/api/v1/test",
            status_code=200,
            duration_ms=10,
            created_at=now,
        )
    )
    db.commit()

    result = get_tenants_matrix(db, None, None)
    by_id = {row["tenantId"]: row for row in result["tenants"]}
    assert by_id[t1.id]["loginFailures"] == 1
    assert by_id[t2.id]["apiRequests"] == 1
