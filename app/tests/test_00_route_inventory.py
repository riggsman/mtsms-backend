import pytest

from server import app


@pytest.mark.integration
def test_route_inventory_has_core_prefixes():
    paths = {r.path for r in app.routes}
    expected = {
        "/auth/v1/login",
        "/api/v1/users",
        "/api/v1/students",
        "/api/v1/teachers",
        "/api/v1/courses",
        "/api/v1/schedules",
        "/api/v1/enrollments",
        "/api/v1/announcements",
        "/api/v1/payments",
        "/api/v1/payroll/report",
    }
    missing = expected - paths
    assert not missing, f"Missing mounted routes: {sorted(missing)}"
