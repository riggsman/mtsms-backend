import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_system_admin_dashboards(sysadmin_client, sysadmin_token):
    hdr = auth_headers(sysadmin_token, tenant="system", institution_id=None)
    assert_ok(sysadmin_client.get("/api/v1/system/stats", headers=hdr), 200)
    assert_ok(sysadmin_client.get("/api/v1/system/recent-tenants", headers=hdr), 200)
    assert_ok(sysadmin_client.get("/api/v1/system/analytics", headers=hdr), 200)


@pytest.mark.integration
def test_subscription_service_lists(sysadmin_client, sysadmin_token):
    hdr = auth_headers(sysadmin_token, tenant="system", institution_id=None)
    assert_ok(sysadmin_client.get("/api/v1/admin/subscription-services?page=1&page_size=10", headers=hdr), 200)
    assert_ok(sysadmin_client.get("/api/v1/admin/service-configurations?page=1&page_size=10", headers=hdr), 200)
