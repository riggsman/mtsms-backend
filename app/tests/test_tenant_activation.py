"""Tests for tenant service activation (access-status, activation patch, guards)."""

import datetime

import pytest
from fastapi import HTTPException

from app.dependencies.tenant_activation import (
    count_activated_features,
    get_platform_support_settings,
    is_tenant_suspended,
    raise_if_tenant_suspended_for_login,
    set_tenant_services_activated,
)
from app.apis.tenant import resume_tenant, suspend_tenant
from app.models.system_settings import SystemSettings
from app.models.tenant import Tenant
from app.models.tenant_audit import TenantAuditEvent
from app.models.user import User
from app.authentication.authenticator import hash_password


@pytest.fixture
def pending_tenant(db):
    tenant = Tenant(
        name="pending_school",
        category="SI",
        domain="pending-school",
        database_url="sqlite:///./pending.db",
        services_activated=False,
        is_active=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def platform_support_settings(db):
    settings = SystemSettings(
        platform_support_email="support@example.com",
        platform_support_phone="+1234567890",
        platform_support_hours="Mon–Fri 9–5",
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@pytest.fixture
def tenant_admin_user(db, pending_tenant):
    user = User(
        institution_id=pending_tenant.id,
        firstname="Tenant",
        lastname="Admin",
        email="tenantadmin@test.com",
        phone="+1000000001",
        username="tenantadmin",
        password=hash_password("admin123"),
        role=["admin"],
        is_active="active",
        gender="Male",
        address="Test",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def pending_tenant_client(db, tenant_admin_user):
    from fastapi.testclient import TestClient
    from server import app
    from app.database.base import get_db_session
    from app.dependencies.auth import get_current_user
    from app.dependencies.tenantDependency import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return tenant_admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_access_status_not_activated(pending_tenant_client, pending_tenant, platform_support_settings):
    response = pending_tenant_client.get("/api/v1/tenant/access-status")
    assert response.status_code == 200
    data = response.json()
    assert data["services_activated"] is False
    assert data["tenant_id"] == pending_tenant.id
    assert data["platform_support_email"] == "support@example.com"
    assert data["platform_support_phone"] == "+1234567890"


def test_activate_requires_at_least_one_feature(db, pending_tenant, monkeypatch):
    monkeypatch.setattr(
        "app.dependencies.tenant_activation.count_activated_features",
        lambda _db, _tenant: 0,
    )
    with pytest.raises(HTTPException) as exc:
        set_tenant_services_activated(
            db,
            pending_tenant,
            activated=True,
            activated_by_user_id=1,
            require_features_when_activating=True,
        )
    assert exc.value.status_code == 400
    assert "at least one service" in str(exc.value.detail).lower()


def test_platform_support_settings_empty_db(db):
    support = get_platform_support_settings(db)
    assert support["platform_support_email"] is None
    assert support["platform_support_phone"] is None


def test_count_activated_features_zero_without_entitlements(db, pending_tenant, monkeypatch):
    monkeypatch.setattr(
        "app.dependencies.tenant_activation.count_effective_features",
        lambda _db, _tenant: 0,
    )
    assert count_activated_features(db, pending_tenant) == 0


@pytest.fixture
def suspended_tenant(db):
    tenant = Tenant(
        name="suspended_school",
        category="SI",
        domain="suspended-school",
        database_url="sqlite:///./suspended.db",
        services_activated=True,
        is_active=False,
        suspension_reason="Policy violation",
        suspended_at=datetime.datetime.utcnow(),
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def suspended_tenant_user(db, suspended_tenant):
    user = User(
        institution_id=suspended_tenant.id,
        firstname="Suspended",
        lastname="User",
        email="suspended@test.com",
        phone="+1000000002",
        username="suspendeduser",
        password=hash_password("pass1234"),
        role=["admin"],
        is_active="active",
        gender="Male",
        address="Test",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def suspended_tenant_client(db, suspended_tenant_user):
    from fastapi.testclient import TestClient
    from server import app
    from app.database.base import get_db_session
    from app.dependencies.auth import get_current_user
    from app.dependencies.tenantDependency import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return suspended_tenant_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def login_client(db):
    """Unauthenticated client for login endpoint tests."""
    from fastapi.testclient import TestClient
    from server import app
    from app.dependencies.tenantDependency import get_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_is_tenant_suspended_true(db, suspended_tenant):
    assert is_tenant_suspended(suspended_tenant, db) is True


def test_access_status_suspended(suspended_tenant_client, suspended_tenant):
    response = suspended_tenant_client.get("/api/v1/tenant/access-status")
    assert response.status_code == 200
    data = response.json()
    assert data["is_suspended"] is True
    assert data["is_active"] is False
    assert data["suspension_reason"] == "Policy violation"
    assert data["suspended_at"] is not None
    assert data["services_activated"] is True


def test_raise_if_tenant_suspended_for_login(db, suspended_tenant_user, suspended_tenant):
    with pytest.raises(HTTPException) as exc:
        raise_if_tenant_suspended_for_login(db, suspended_tenant_user)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "TENANT_SUSPENDED"


def test_login_blocked_when_tenant_suspended(login_client, suspended_tenant_user, suspended_tenant):
    response = login_client.post(
        "/auth/v1/login",
        json={"username": "suspendeduser", "password": "pass1234"},
        headers={"X-Tenant-Name": suspended_tenant.name},
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["code"] == "TENANT_SUSPENDED"


def test_suspend_resume_writes_audit(db, pending_tenant, test_system_admin):
    tenant = suspend_tenant(
        db,
        pending_tenant.id,
        reason="Test suspension",
        actor_user_id=test_system_admin.id,
    )
    assert tenant.is_active is False
    events = (
        db.query(TenantAuditEvent)
        .filter(TenantAuditEvent.tenant_id == pending_tenant.id)
        .order_by(TenantAuditEvent.id.asc())
        .all()
    )
    assert len(events) == 1
    assert events[0].action == "suspend"
    assert events[0].reason == "Test suspension"
    assert events[0].actor_user_id == test_system_admin.id

    resume_tenant(db, pending_tenant.id, actor_user_id=test_system_admin.id)
    events = (
        db.query(TenantAuditEvent)
        .filter(TenantAuditEvent.tenant_id == pending_tenant.id)
        .order_by(TenantAuditEvent.id.asc())
        .all()
    )
    assert len(events) == 2
    assert events[1].action == "resume"
