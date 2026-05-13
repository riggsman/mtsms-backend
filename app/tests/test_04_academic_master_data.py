import pytest

from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers
from app.tests.helpers.seed import ensure_department


@pytest.mark.integration
def test_department_course_teacher_student_lists(client, admin_token, db):
    ensure_department(db)
    assert_ok(client.get("/api/v1/departments?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
    assert_ok(client.get("/api/v1/courses?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
    assert_ok(client.get("/api/v1/teachers?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
    assert_ok(client.get("/api/v1/students?page=1&page_size=10", headers=auth_headers(admin_token)), 200)


@pytest.mark.integration
def test_classes_and_specializations_list(client, admin_token):
    assert_ok(client.get("/api/v1/classes?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
    assert_ok(client.get("/api/v1/specializations?page=1&page_size=10", headers=auth_headers(admin_token)), 200)
