import pytest

from app.tests.helpers.assertions import assert_auth_denied, assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_users_list_and_get(client, admin_token, test_admin_user):
    list_resp = client.get("/api/v1/users?page=1&page_size=10", headers=auth_headers(admin_token))
    assert_ok(list_resp, 200)
    get_resp = client.get(f"/api/v1/users/{test_admin_user.id}", headers=auth_headers(admin_token))
    assert_ok(get_resp, 200)


@pytest.mark.integration
def test_users_endpoint_denies_student(client_student):
    r = client_student.get("/api/v1/users", headers=auth_headers())
    assert_auth_denied(r)
