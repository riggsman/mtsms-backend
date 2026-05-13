import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_student_dashboard_overview_and_alerts(client_student, student_token):
    overview = client_student.get("/api/v1/student-dashboard/overview?view_mode=today", headers=auth_headers(student_token))
    assert_ok(overview, 200)
    assert "next_actions" in overview.json()

    alerts = client_student.get("/api/v1/student-dashboard/alerts", headers=auth_headers(student_token))
    assert_ok(alerts, 200)
    assert "alerts" in alerts.json()


@pytest.mark.integration
def test_student_dashboard_history_analytics_search_export(client_student, student_token):
    history = client_student.get("/api/v1/student-dashboard/history?page=1&page_size=10", headers=auth_headers(student_token))
    assert_ok(history, 200)
    assert "items" in history.json()

    analytics = client_student.get("/api/v1/student-dashboard/analytics", headers=auth_headers(student_token))
    assert_ok(analytics, 200)
    assert "grade_context" in analytics.json()

    search = client_student.get("/api/v1/student-dashboard/search?q=math&limit=5", headers=auth_headers(student_token))
    assert_ok(search, 200)
    assert "items" in search.json()

    export = client_student.get("/api/v1/student-dashboard/export/performance-summary", headers=auth_headers(student_token))
    assert_ok(export, 200)
    assert "summary" in export.json()
