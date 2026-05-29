"""
Backend tests for FCM: public firebase-web-config and JWT token registration.
Uses in-memory SQLite with dependency overrides (including get_db_session).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server import app
from app.database.base import Base as DefaultBase, get_db_session
from app.database.sessionManager import BaseModel_Base
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.models.user_push_token import UserPushToken
from app.authentication.authenticator import hash_password

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_FcmSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture
def fcm_db():
    DefaultBase.metadata.create_all(bind=_engine)
    BaseModel_Base.metadata.create_all(bind=_engine)
    db = _FcmSessionLocal()
    try:
        yield db
    finally:
        db.close()
        DefaultBase.metadata.drop_all(bind=_engine)
        BaseModel_Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def fcm_client(fcm_db):
    """Tenant + global DB are the same SQLite session (matches test conftest pattern)."""

    user = User(
        institution_id=1,
        firstname="Admin",
        lastname="User",
        email="fcm-admin@test.com",
        phone="+10000000001",
        username="fcm_admin",
        password=hash_password("pass12345"),
        role=["admin"],
        is_active="active",
        gender="Male",
        address="Addr",
    )
    fcm_db.add(user)
    fcm_db.commit()
    fcm_db.refresh(user)

    def override_session():
        try:
            yield fcm_db
        finally:
            pass

    def override_user():
        return user

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_db] = override_session
    app.dependency_overrides[get_current_user_tenant] = override_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def _seed_settings(fcm_db, **firebase_fields):
    row = SystemSettings(
        maintenance_mode=False,
        allow_new_registrations=True,
        max_tenants=10,
        session_timeout=30,
        email_notifications=True,
        cache_timeout=5,
        inactivity_timeout=5,
        maintenance_check_interval=60,
        access_token_expire_minutes=60,
        refresh_token_expire_days=7,
        cache_version="1",
        **firebase_fields,
    )
    fcm_db.add(row)
    fcm_db.commit()


def test_firebase_web_config_disabled_when_messaging_off(fcm_db, fcm_client):
    _seed_settings(fcm_db, firebase_messaging_enabled=False)
    r = fcm_client.get("/system/firebase-web-config")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is False
    assert data.get("web") in (None, {})


def test_firebase_web_config_enabled_when_complete(fcm_db, fcm_client):
    _seed_settings(
        fcm_db,
        firebase_messaging_enabled=True,
        firebase_api_key="test-api-key",
        firebase_auth_domain="demo.firebaseapp.com",
        firebase_project_id="demo-proj",
        firebase_messaging_sender_id="1234567890",
        firebase_app_id="1:123:web:abc",
        firebase_vapid_key="BTestVapidKeyPublic",
    )
    r = fcm_client.get("/system/firebase-web-config")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    assert data["web"]["apiKey"] == "test-api-key"
    assert data["web"]["authDomain"] == "demo.firebaseapp.com"
    assert data["web"]["projectId"] == "demo-proj"
    assert data["web"]["messagingSenderId"] == "1234567890"
    assert data["web"]["appId"] == "1:123:web:abc"
    assert data["web"]["storageBucket"] == "demo-proj.appspot.com"
    assert data["vapidKey"] == "BTestVapidKeyPublic"


def test_fcm_token_register_403_when_messaging_disabled(fcm_db, fcm_client):
    _seed_settings(fcm_db, firebase_messaging_enabled=False)
    r = fcm_client.post(
        "//notifications/fcm-token",
        json={"token": "a" * 20, "user_agent": "pytest"},
    )
    assert r.status_code == 403


def test_fcm_token_register_204_when_enabled(fcm_db, fcm_client):
    _seed_settings(
        fcm_db,
        firebase_messaging_enabled=True,
        firebase_api_key="k",
        firebase_auth_domain="d.firebaseapp.com",
        firebase_project_id="p",
        firebase_messaging_sender_id="1",
        firebase_app_id="1:1:web:x",
        firebase_vapid_key=None,
    )
    token = "d" * 32  # min length 10 in schema
    r = fcm_client.post(
        "/notifications/fcm-token",
        json={"token": token, "user_agent": "pytest-client"},
    )
    assert r.status_code == 204
    row = fcm_db.query(UserPushToken).filter(UserPushToken.token == token).first()
    assert row is not None
    uid = fcm_db.query(User).filter(User.username == "fcm_admin").first().id
    assert row.user_id == uid


def test_notifications_test_push_forbidden_when_messaging_disabled(fcm_db, fcm_client):
    _seed_settings(fcm_db, firebase_messaging_enabled=False)
    r = fcm_client.post("/notifications/test-push")
    assert r.status_code == 403


def test_notifications_test_push_no_tokens(fcm_db, fcm_client):
    _seed_settings(
        fcm_db,
        firebase_messaging_enabled=True,
        firebase_api_key="k",
        firebase_auth_domain="d.firebaseapp.com",
        firebase_project_id="p",
        firebase_messaging_sender_id="1",
        firebase_app_id="1:1:web:x",
    )
    r = fcm_client.post("/notifications/test-push")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["reason"] == "no_tokens"


def test_notifications_test_push_admin_sdk_missing(fcm_db, fcm_client, monkeypatch):
    """With tokens but Admin SDK unavailable, expect admin_sdk_not_configured."""
    monkeypatch.setattr(
        "app.services.fcm_service.ensure_firebase_admin_initialized",
        lambda: False,
    )
    _seed_settings(
        fcm_db,
        firebase_messaging_enabled=True,
        firebase_api_key="k",
        firebase_auth_domain="d.firebaseapp.com",
        firebase_project_id="p",
        firebase_messaging_sender_id="1",
        firebase_app_id="1:1:web:x",
    )
    import datetime
    from app.models.user_push_token import UserPushToken

    uid = fcm_db.query(User).filter(User.username == "fcm_admin").first().id
    fcm_db.add(
        UserPushToken(
            user_id=uid,
            institution_id=1,
            token="f" * 32,
            user_agent="pytest",
            created_at=datetime.datetime.utcnow(),
            last_seen_at=datetime.datetime.utcnow(),
        )
    )
    fcm_db.commit()
    r = fcm_client.post("/notifications/test-push")
    assert r.status_code == 200
    data = r.json()
    assert data["reason"] == "admin_sdk_not_configured"


def test_fcm_token_delete(fcm_db, fcm_client):
    _seed_settings(
        fcm_db,
        firebase_messaging_enabled=True,
        firebase_api_key="k",
        firebase_auth_domain="d.firebaseapp.com",
        firebase_project_id="p",
        firebase_messaging_sender_id="1",
        firebase_app_id="1:1:web:x",
    )
    token = "e" * 32
    fcm_client.post("/notifications/fcm-token", json={"token": token})
    r = fcm_client.delete(f"/notifications/fcm-token?token={token}")
    assert r.status_code == 204
    assert fcm_db.query(UserPushToken).filter(UserPushToken.token == token).first() is None
