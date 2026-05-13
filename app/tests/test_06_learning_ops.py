import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_learning_communication_lists(client, admin_token):
    hdr = auth_headers(admin_token)
    assert_ok(client.get("/api/v1/assignments?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/notes?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/announcements?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/complaints?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/activities?page=1&page_size=10", headers=hdr), 200)
