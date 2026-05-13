import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers
from app.tests.helpers.test_data import branch_create_payload, tenant_settings_update_payload


@pytest.mark.integration
def test_tenant_settings_and_status(client, admin_token):
    get_resp = client.get("/api/v1/tenant-settings", headers=auth_headers(admin_token))
    assert_ok(get_resp, 200)

    put_resp = client.put(
        "/api/v1/tenant-settings",
        json=tenant_settings_update_payload(),
        headers=auth_headers(admin_token),
    )
    assert_ok(put_resp, 200)

    status_resp = client.get("/api/v1/tenant-settings/status", headers=auth_headers(admin_token))
    assert_ok(status_resp, 200)


@pytest.mark.integration
def test_branch_crud(client, admin_token):
    create = client.post(
        "/api/v1/branches",
        json=branch_create_payload(),
        headers=auth_headers(admin_token),
    )
    assert create.status_code in (201, 409)

    list_resp = client.get("/api/v1/branches", headers=auth_headers(admin_token))
    assert_ok(list_resp, 200)
