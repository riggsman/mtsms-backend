import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_get_users(client, admin_token):
    response = client.get("/api/v1/users?page=1&page_size=10", headers=auth_headers(admin_token))
    assert_ok(response, 200)
    payload = response.json()
    assert isinstance(payload.get("items"), list)


@pytest.mark.integration
def test_get_user_by_id(client, admin_token, test_admin_user):
    response = client.get(f"/api/v1/users/{test_admin_user.id}", headers=auth_headers(admin_token))
    assert_ok(response, 200)
    assert response.json()["id"] == test_admin_user.id


@pytest.mark.integration
def test_students_can_list_users_in_shared_mode(client_student, student_token):
    response = client_student.get("/api/v1/users", headers=auth_headers(student_token))
    assert_ok(response, 200)
