import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_payroll_status_entries_report(client_staff, client, staff_token, admin_token):
    assert_ok(client_staff.get("/api/v1/payroll/me/status", headers=auth_headers(staff_token)), 200)
    assert_ok(client_staff.get("/api/v1/payroll/me/entries?page=1&page_size=10", headers=auth_headers(staff_token)), 200)
    assert_ok(
        client.get("/api/v1/payroll/report?from_date=2026-01-01&to_date=2026-12-31", headers=auth_headers(admin_token)),
        200,
    )
