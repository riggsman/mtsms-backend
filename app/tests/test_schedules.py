import pytest
from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_get_schedules(client, admin_token):
    response = client.get("/api/v1/schedules?page=1&page_size=10", headers=auth_headers(admin_token))
    assert_ok(response, 200)
    assert isinstance(response.json().get("items"), list)


@pytest.mark.integration
def test_student_can_get_schedules(client_student, student_token):
    response = client_student.get("/api/v1/schedules?page=1&page_size=10", headers=auth_headers(student_token))
    assert_ok(response, 200)
