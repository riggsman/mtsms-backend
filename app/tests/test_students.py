import datetime

import pytest
from app.models.school import School, SchoolFee
from app.models.student import Student
from app.tests.helpers.assertions import assert_ok
from app.tests.helpers.http import auth_headers


@pytest.mark.integration
def test_list_students(client, admin_token):
    response = client.get("/api/v1/students?page=1&page_size=10", headers=auth_headers(admin_token))
    assert_ok(response, 200)
    assert isinstance(response.json().get("items"), list)


@pytest.mark.integration
def test_staff_can_list_students(client_staff, staff_token):
    response = client_staff.get("/api/v1/students?page=1&page_size=10", headers=auth_headers(staff_token))
    assert_ok(response, 200)


@pytest.mark.integration
def test_student_me_endpoint(client_student, student_token):
    response = client_student.get("/api/v1/students/me", headers=auth_headers(student_token))
    assert response.status_code in (200, 403)


@pytest.mark.integration
def test_student_my_program_fee_endpoint(client_student, db, test_student_user):
    school = School(
        institution_id=1,
        name="Engineering",
        code="ENG",
        description="Engineering faculty"
    )
    db.add(school)
    db.commit()
    db.refresh(school)

    student = Student(
        institution_id=1,
        school_id=school.id,
        firstname="Student",
        lastname="User",
        dob="2000-01-01",
        gender="Male",
        address="Test Address",
        email=test_student_user.email,
        phone="+1234567892",
        student_id="STU001",
        class_id=1,
        level="HND",
        type="Undergraduate",
        department_id=1,
        academic_year_id=1,
        guardian_id=1
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    fee = SchoolFee(
        school_id=school.id,
        level="HND",
        fee_amount=250000,
        fee_deadline=datetime.datetime(2026, 12, 31)
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)

    response = client_student.get("/api/v1/students/me/program-fee")
    assert_ok(response, 200)
    payload = response.json()
    assert payload["school_id"] == school.id
    assert payload["level"] == "HND"
    assert payload["fee_amount"] == 250000.0


@pytest.mark.integration
def test_school_fees_filter_by_level(client, db, admin_token):
    school = School(
        institution_id=1,
        name="Business",
        code="BUS",
        description="Business faculty"
    )
    db.add(school)
    db.commit()
    db.refresh(school)

    fee_hnd = SchoolFee(school_id=school.id, level="HND", fee_amount=150000)
    fee_degree = SchoolFee(school_id=school.id, level="DEGREE", fee_amount=200000)
    db.add_all([fee_hnd, fee_degree])
    db.commit()

    response = client.get(f"/api/v1/schools/{school.id}/fees?level=HND", headers=auth_headers(admin_token))
    assert_ok(response, 200)
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["level"] == "HND"
    assert payload[0]["fee_amount"] == 150000.0
