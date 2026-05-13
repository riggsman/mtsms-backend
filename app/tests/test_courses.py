import pytest
from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_get_courses(client, admin_token):
    response = client.get("/api/v1/courses?page=1&page_size=10", headers=auth_headers(admin_token))
    assert_ok(response, 200)
    payload = response.json()
    assert isinstance(payload.get("items"), list)


@pytest.mark.integration
def test_get_course_by_id_when_present(client, admin_token):
    listing = client.get("/api/v1/courses?page=1&page_size=10", headers=auth_headers(admin_token))
    assert_ok(listing, 200)
    items = listing.json().get("items", [])
    if not items:
        pytest.skip("No seeded course available to fetch by id.")
    course_id = items[0]["id"]
    single = client.get(f"/api/v1/courses/{course_id}", headers=auth_headers(admin_token))
    assert_ok(single, 200)
