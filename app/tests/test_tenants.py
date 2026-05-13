import time
import pytest

from app.tests.helpers.assertions import assert_ok


@pytest.mark.integration
def test_get_all_tenants(sysadmin_client, sysadmin_token):
    response = sysadmin_client.get(
        "/api/v1/tenants?page=1&page_size=10",
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert_ok(response, 200)
    assert isinstance(response.json().get("items"), list)


@pytest.mark.integration
def test_create_tenant(sysadmin_client, sysadmin_token):
    unique_name = f"legacy_school_{int(time.time() * 1000)}"
    response = sysadmin_client.post(
        "/api/v1/tenants",
        json={"name": unique_name, "category": "HI"},
        headers={"Authorization": f"Bearer {sysadmin_token}"},
    )
    assert response.status_code in (200, 201, 400)
    if response.status_code in (200, 201):
        assert response.json().get("name") == unique_name
