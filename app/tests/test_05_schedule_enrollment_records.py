import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_schedule_enrollment_student_record_lists(client, admin_token):
    assert_ok(client.get("/api/v1/schedules?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
    assert_ok(client.get("/api/v1/enrollments?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
    assert_ok(client.get("/api/v1/student-records?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
