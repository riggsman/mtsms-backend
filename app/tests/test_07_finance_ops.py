import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_finance_endpoint_lists(client, admin_token):
    hdr = auth_headers(admin_token)
    assert_ok(client.get("/api/v1/payments?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/fee-structure/?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/schools?page=1&page_size=10", headers=hdr), 200)
    assert_ok(client.get("/api/v1/student-payments?page=1&page_size=10", headers=hdr), 200)
