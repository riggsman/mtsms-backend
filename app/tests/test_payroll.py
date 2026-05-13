"""Tests for payroll code-based course clock and report APIs."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.department import Department
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.payroll_time_entry import PayrollTimeEntry
from app.apis import payroll as payroll_api
from app.tests.helpers.test_data import (
    payroll_clock_in_payload,
    payroll_clock_out_payload,
    payroll_generate_codes_payload,
)


@pytest.fixture
def payroll_teacher(db, test_tenant, test_staff_user):
    """Lecturer row linked to test_staff_user (same email + institution)."""
    dep = Department(
        institution_id=test_tenant.id,
        name="Payroll Test Dept",
        code="PAYROLL01",
    )
    db.add(dep)
    db.flush()
    teacher = Teacher(
        institution_id=test_staff_user.institution_id,
        department_id=dep.id,
        email=test_staff_user.email,
        firstname=test_staff_user.firstname,
        lastname=test_staff_user.lastname,
        phone=test_staff_user.phone,
        gender=test_staff_user.gender,
        address=test_staff_user.address,
        dob="1990-01-01",
        employee_id="EMP-PAY-01",
        hourly_rate=Decimal("10.00"),
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@pytest.fixture
def payroll_course(db, test_tenant):
    dep = Department(
        institution_id=test_tenant.id,
        name="Payroll Course Dept",
        code="PAYROLL02",
    )
    db.add(dep)
    db.flush()
    course = Course(
        institution_id=test_tenant.id,
        name="Payroll Testing",
        code="PAY101",
        department_id=dep.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def payroll_student(db, test_student_user):
    student = Student(
        institution_id=test_student_user.institution_id,
        school_id=1,
        firstname=test_student_user.firstname,
        lastname=test_student_user.lastname,
        dob="2000-01-01",
        gender=test_student_user.gender,
        address=test_student_user.address,
        email=test_student_user.email,
        phone=test_student_user.phone,
        student_id="STD-PAY-001",
        class_id=1,
        level="100",
        type="Undergraduate",
        department_id=1,
        specialization_id=None,
        academic_year_id=1,
        guardian_id=1,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@pytest.fixture
def payroll_enrollment(db, payroll_student, payroll_course):
    enr = Enrollment(
        institution_id=payroll_student.institution_id,
        student_id=payroll_student.id,
        course_id=payroll_course.id,
        status="active",
    )
    db.add(enr)
    db.commit()
    db.refresh(enr)
    return enr


def test_code_generation_requires_admin(client_staff, payroll_teacher, payroll_course):
    r = client_staff.post(
        "/api/v1/payroll/codes/generate",
        json=payroll_generate_codes_payload(payroll_teacher.id, payroll_course.code),
    )
    assert r.status_code == 403


def test_full_dual_confirmation_flow(
    client, client_staff, client_student, payroll_teacher, payroll_course, payroll_enrollment
):
    gen = client.post(
        "/api/v1/payroll/codes/generate",
        json=payroll_generate_codes_payload(payroll_teacher.id, payroll_course.code),
    )
    assert gen.status_code == 200
    codes = gen.json()

    wrong_in = client_staff.post(
        "/api/v1/payroll/clock-in",
        json=payroll_clock_in_payload(payroll_course.code, "99999"),
    )
    assert wrong_in.status_code in (403, 422)

    cin = client_staff.post(
        "/api/v1/payroll/clock-in",
        json=payroll_clock_in_payload(payroll_course.code, codes["clock_in_code"]),
    )
    assert cin.status_code == 200

    lco = client_staff.post(
        "/api/v1/payroll/clock-out/lecturer",
        json=payroll_clock_out_payload(payroll_course.code, codes["clock_out_code"]),
    )
    assert lco.status_code == 200
    assert lco.json().get("clock_out_at") is None

    sco = client_student.post(
        "/api/v1/payroll/clock-out/student",
        json=payroll_clock_out_payload(payroll_course.code, codes["clock_out_code"]),
    )
    assert sco.status_code == 200
    assert sco.json().get("clock_out_at") is not None

    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = client.get(f"/api/v1/payroll/report?from_date={today}&to_date={today}")
    assert r.status_code == 200
    payload = r.json()
    rows = payload.get("rows", [])
    assert any(row["teacher_id"] == payroll_teacher.id for row in rows)
    match = next(row for row in rows if row["teacher_id"] == payroll_teacher.id)
    assert match["gross_pay"] is not None
    assert float(match["total_hours"]) >= 0


def test_clock_in_code_is_single_use(client, client_staff, payroll_teacher, payroll_course):
    gen = client.post(
        "/api/v1/payroll/codes/generate",
        json=payroll_generate_codes_payload(payroll_teacher.id, payroll_course.code),
    )
    assert gen.status_code == 200
    code = gen.json()["clock_in_code"]
    first = client_staff.post(
        "/api/v1/payroll/clock-in",
        json=payroll_clock_in_payload(payroll_course.code, code),
    )
    assert first.status_code == 200
    second = client_staff.post(
        "/api/v1/payroll/clock-in",
        json=payroll_clock_in_payload(payroll_course.code, code),
    )
    assert second.status_code in (403, 409)


def test_generated_codes_expire_after_30_minutes(
    db, client, client_staff, payroll_teacher, payroll_course
):
    gen = client.post(
        "/api/v1/payroll/codes/generate",
        json=payroll_generate_codes_payload(payroll_teacher.id, payroll_course.code),
    )
    assert gen.status_code == 200
    payload = gen.json()
    entry = (
        db.query(PayrollTimeEntry)
        .filter(PayrollTimeEntry.id == payload["entry_id"])
        .first()
    )
    entry.codes_generated_at = datetime.utcnow() - timedelta(minutes=31)
    entry.codes_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    r = client_staff.post(
        "/api/v1/payroll/clock-in",
        json=payroll_clock_in_payload(payroll_course.code, payload["clock_in_code"]),
    )
    assert r.status_code == 409




def test_auto_generated_code_uses_30_min_ttl(db, payroll_teacher, payroll_course):
    entry = payroll_api.auto_generate_codes_for_schedule(
        db,
        institution_id=payroll_teacher.institution_id,
        teacher_id=payroll_teacher.id,
        course_code=payroll_course.code,
    )
    assert entry is not None
    delta = entry.codes_expires_at - entry.codes_generated_at
    assert 29 <= (delta.total_seconds() / 60) <= 31


def test_payroll_codes_audit_requires_admin(client_staff, payroll_teacher, payroll_course):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = client_staff.get(
        f"/api/v1/payroll/codes/audit?from_date={today}&to_date={today}",
    )
    assert r.status_code == 403


def test_payroll_codes_audit_lists_issuance(client, payroll_teacher, payroll_course):
    gen = client.post(
        "/api/v1/payroll/codes/generate",
        json=payroll_generate_codes_payload(payroll_teacher.id, payroll_course.code),
    )
    assert gen.status_code == 200
    gj = gen.json()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    r = client.get(
        f"/api/v1/payroll/codes/audit?from_date={today}&to_date={today}&page=1&page_size=20",
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("total", 0) >= 1
    row = next(x for x in body["items"] if x["entry_id"] == gj["entry_id"])
    assert row["clock_in_code_used"] is False
    assert row["clock_out_code_used"] is False
    assert row["clock_in_code_plain"] == gj["clock_in_code"]
    assert row["clock_out_code_plain"] == gj["clock_out_code"]
    assert row["codes_generated_at"] is not None
