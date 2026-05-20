"""Ensure /api/v1/system/settings reads and writes the system_settings table."""

from app.models.system_settings import SystemSettings


def test_get_system_settings_returns_full_row(sysadmin_client, db):
    row = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    if row is None:
        row = SystemSettings()
        db.add(row)
    row.maintenance_mode = True
    row.allow_new_registrations = False
    row.max_tenants = 50
    row.session_timeout = 45
    row.email_notifications = False
    row.cache_timeout = 10
    row.inactivity_timeout = 15
    row.maintenance_check_interval = 120
    row.access_token_expire_minutes = 90
    row.refresh_token_expire_days = 14
    row.platform_support_email = "support@test.com"
    row.platform_support_phone = "+123"
    row.platform_support_hours = "9-5"
    row.cache_version = "42"
    db.commit()
    db.refresh(row)

    response = sysadmin_client.get("/api/v1/system/settings")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == row.id
    assert data["maintenanceMode"] is True
    assert data["allowNewRegistrations"] is False
    assert data["maxTenants"] == 50
    assert data["sessionTimeout"] == 45
    assert data["emailNotifications"] is False
    assert data["cacheTimeout"] == 10
    assert data["inactivityTimeout"] == 15
    assert data["maintenanceCheckInterval"] == 120
    assert data["accessTokenExpireMinutes"] == 90
    assert data["refreshTokenExpireDays"] == 14
    assert data["platformSupportEmail"] == "support@test.com"
    assert data["platformSupportPhone"] == "+123"
    assert data["platformSupportHours"] == "9-5"
    assert data["cacheVersion"] == "42"


def test_put_system_settings_persists_platform_support(sysadmin_client, db):
    payload = {
        "maintenanceMode": False,
        "allowNewRegistrations": True,
        "maxTenants": 100,
        "sessionTimeout": 30,
        "emailNotifications": True,
        "platformSupportEmail": "help@platform.test",
        "platformSupportPhone": "+237600000000",
        "platformSupportHours": "Mon-Fri 9-5",
    }

    response = sysadmin_client.put("/api/v1/system/settings", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["platformSupportEmail"] == "help@platform.test"
    assert data["platformSupportPhone"] == "+237600000000"
    assert data["platformSupportHours"] == "Mon-Fri 9-5"

    row = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    assert row is not None
    assert row.platform_support_email == "help@platform.test"
    assert row.platform_support_phone == "+237600000000"
    assert row.platform_support_hours == "Mon-Fri 9-5"
