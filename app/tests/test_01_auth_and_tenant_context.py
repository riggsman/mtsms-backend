import pytest

from app.tests.helpers.assertions import assert_auth_denied, assert_ok
from app.tests.helpers.http import auth_headers
from app.tests.helpers.test_data import (
    auth_login_payload,
    refresh_token_payload,
    verify_token_payload,
)


@pytest.mark.integration
def test_login_verify_refresh_flow(client, test_admin_user):
    login = client.post(
        "/auth/v1/login",
        json=auth_login_payload(),
        headers={"X-Tenant-Name": "test_school"},
    )
    assert_ok(login, 200)
    token = login.json()["access_token"]

    verify = client.post("/auth/v1/verify_token", json=verify_token_payload(token))
    assert_ok(verify, 200)

    refresh = client.post("/auth/v1/refresh", json=refresh_token_payload(login.json()["refresh_token"]))
    assert_ok(refresh, 200)


@pytest.mark.integration
def test_tenant_scoped_route_requires_auth(client):
    r = client.get("/api/v1/users", headers={"X-Tenant-Name": "test_school"})
    assert_auth_denied(r)


@pytest.mark.integration
def test_health_endpoints(client):
    assert_ok(client.get("/"), 200)
    assert_ok(client.get("/api/v1/health"), 200)
