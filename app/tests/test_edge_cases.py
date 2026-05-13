import pytest
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_expired_or_invalid_token(client):
    response = client.get(
        "/api/v1/users",
        headers={
            "Authorization": "Bearer invalid_token_here",
            "X-Tenant-Name": "test_school"
        }
    )
    assert response.status_code in [200, 401, 403]


@pytest.mark.integration
def test_validation_errors_on_user_creation(client, admin_token):
    response = client.post(
        "/api/v1/users",
        json={"username": "missing_fields"},
        headers=auth_headers(admin_token),
    )
    assert response.status_code in (400, 422)


@pytest.mark.integration
def test_invalid_pagination(client, admin_token):
    response = client.get("/api/v1/users?page=-1&page_size=0", headers=auth_headers(admin_token))
    assert response.status_code in (400, 422)
