import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.test_data import auth_login_payload, refresh_token_payload, verify_token_payload


@pytest.mark.integration
def test_login_success(client, test_admin_user):
    response = client.post(
        "/auth/v1/login",
        json=auth_login_payload(),
        headers={"X-Tenant-Name": "test_school"},
    )
    assert_ok(response, 200)
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload.get("access_token")
    assert payload.get("refresh_token")


@pytest.mark.integration
def test_login_invalid_credentials(client, test_admin_user):
    response = client.post(
        "/auth/v1/login",
        json=auth_login_payload(password="wrongpassword"),
        headers={"X-Tenant-Name": "test_school"},
    )
    assert response.status_code in (400, 401)


@pytest.mark.integration
def test_verify_and_refresh_flow(client, admin_token):
    verify = client.post("/auth/v1/verify_token", json=verify_token_payload(admin_token))
    assert_ok(verify, 200)

    login = client.post(
        "/auth/v1/login",
        json=auth_login_payload(),
        headers={"X-Tenant-Name": "test_school"},
    )
    assert_ok(login, 200)
    refresh = client.post(
        "/auth/v1/refresh",
        json=refresh_token_payload(login.json()["refresh_token"]),
    )
    assert_ok(refresh, 200)
