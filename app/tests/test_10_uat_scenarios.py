import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.uat
def test_uat_admin_setup_and_visibility(client, admin_token):
    hdr = auth_headers(admin_token)
    assert_ok(client.get("/api/v1/tenant-settings", headers=hdr), 200)
    assert_ok(client.get("/api/v1/departments?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/courses?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/schedules?page=1&page_size=10", headers=hdr), 200)


@pytest.mark.uat
def test_uat_student_journey(client_student, student_token):
    hdr = auth_headers(student_token)
    assert_ok(client_student.get("/api/v1/students/me", headers=hdr), 200)
    assert_ok(client_student.get("/api/v1/schedules?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client_student.get("/api/v1/announcements?page=1&page_size=10", headers=hdr), 200)


@pytest.mark.uat
def test_uat_staff_payroll_and_reports(client_staff, client, staff_token, admin_token):
    assert_ok(client_staff.get("/api/v1/payroll/me/status", headers=auth_headers(staff_token)), 200)
    assert_ok(
        client.get("/api/v1/payroll/report?from_date=2026-01-01&to_date=2026-12-31", headers=auth_headers(admin_token)),
        200,
    )
