"""
Comprehensive multi-tenant database seeder.
Populates core tables with valid relationships and is safe to re-run.
"""
import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.authentication.authenticator import hash_password
from app.database.base import DefaultSessionLocal
from app.models.academic_year import AcademicYear
from app.models.activity import Activity
from app.models.announcement import Announcement
from app.models.assignment import Assignment
from app.models.branch import Branch
from app.models.classes import Class
from app.models.complaint import Complaint
from app.models.course import Course
from app.models.department import Department
from app.models.enrollment import Enrollment
from app.models.guardian import Guardian
from app.models.note import Note
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.student_record import StudentRecord
from app.models.teacher import Teacher
from app.models.tenant import Tenant
from app.models.user import User


def _get_or_create(db, model, lookup: dict, defaults: dict):
    row = db.query(model).filter_by(**lookup).first()
    if row:
        return row, False
    payload = {**defaults, **lookup}
    row = model(**payload)
    db.add(row)
    db.flush()
    return row, True


def _seed_tenant_bundle(
    db,
    *,
    now: datetime,
    tenant_name: str,
    tenant_domain: str,
    tenant_category: str,
    branch_name: str,
    dept_a_name: str,
    dept_a_code_suffix: str,
    dept_b_name: str,
    dept_b_code_suffix: str,
    class_code: str,
    class_name: str,
    class_level: str,
    guardian_phone: str,
    guardian_name: str,
    teacher_firstname: str,
    teacher_lastname: str,
    teacher_email_local: str,
    teacher_phone: str,
    teacher_employee_id: str,
    student_reg: str,
    student_firstname: str,
    student_lastname: str,
    student_email_local: str,
    student_phone: str,
    course_a_code: str,
    course_a_name: str,
    course_b_code: str,
    course_b_name: str,
    schedule_day: str,
):
    tenant, _ = _get_or_create(
        db,
        Tenant,
        {"name": tenant_name},
        {
            "category": tenant_category,
            "domain": tenant_domain,
            "is_active": True,
            "fee_amount": 120000,
            "created_at": now,
        },
    )
    branch, _ = _get_or_create(
        db,
        Branch,
        {"institution_id": tenant.id, "name": branch_name},
        {"code": f"BR_{tenant.id}", "is_active": True, "sort_order": 0, "created_at": now},
    )
    dept_a, _ = _get_or_create(
        db,
        Department,
        {"code": f"{tenant.id}_{dept_a_code_suffix}"},
        {"institution_id": tenant.id, "name": dept_a_name, "description": f"{dept_a_name} Department", "created_at": now},
    )
    dept_b, _ = _get_or_create(
        db,
        Department,
        {"code": f"{tenant.id}_{dept_b_code_suffix}"},
        {"institution_id": tenant.id, "name": dept_b_name, "description": f"{dept_b_name} Department", "created_at": now},
    )
    year_1, _ = _get_or_create(
        db,
        AcademicYear,
        {"institution_id": tenant.id, "name": "2025/2026"},
        {"start_date": "2025-09-01", "end_date": "2026-06-30", "is_current": True, "created_at": now},
    )
    class_1, _ = _get_or_create(
        db,
        Class,
        {"institution_id": tenant.id, "code": class_code},
        {
            "name": class_name,
            "institution_level": class_level,
            "category": class_level,
            "is_custom": True,
            "capacity": 120,
            "academic_year_id": year_1.id,
            "department_id": dept_b.id,
            "created_at": now,
        },
    )
    guardian_1, _ = _get_or_create(
        db,
        Guardian,
        {"institution_id": tenant.id, "phone": guardian_phone},
        {
            "guardian_name": guardian_name,
            "address": "City Center",
            "relationship": "mother",
            "gender": "Female",
            "email": f"guardian_{tenant.id}@{tenant_domain}.local",
            "created_at": now,
        },
    )
    teacher_1, _ = _get_or_create(
        db,
        Teacher,
        {"employee_id": teacher_employee_id},
        {
            "institution_id": tenant.id,
            "branch_id": branch.id,
            "firstname": teacher_firstname,
            "lastname": teacher_lastname,
            "middlename": "",
            "dob": "1987-05-10",
            "gender": "Male",
            "address": "Faculty Block",
            "email": f"{teacher_email_local}@{tenant_domain}.local",
            "phone": teacher_phone,
            "department_id": dept_b.id,
            "employee_id": teacher_employee_id,
            "position": "Lecturer",
            "qualification": "MSc",
            "specialization": dept_b_name,
            "created_at": now,
        },
    )
    admin_user, _ = _get_or_create(
        db,
        User,
        {"email": f"admin{tenant.id}@{tenant_domain}.local"},
        {
            "institution_id": tenant.id,
            "branch_id": branch.id,
            "department_id": dept_b.id,
            "firstname": "Tenant",
            "lastname": "Admin",
            "middlename": "",
            "gender": "Male",
            "address": "Head Office",
            "phone": f"+23767000{tenant.id:04d}",
            "username": f"tenant_admin_{tenant.id}",
            "password": hash_password("Admin@1234"),
            "role": ["super_admin"],
            "user_type": "TENANT",
            "is_active": "active",
            "must_change_password": "false",
            "language": "en",
            "created_at": now,
        },
    )
    student_1, _ = _get_or_create(
        db,
        Student,
        {"student_id": student_reg},
        {
            "institution_id": tenant.id,
            "branch_id": branch.id,
            "school_id": 1,
            "firstname": student_firstname,
            "lastname": student_lastname,
            "middlename": "",
            "dob": "2006-08-21",
            "gender": "Female",
            "address": "Student Quarters",
            "email": f"{student_email_local}@{tenant_domain}.local",
            "phone": student_phone,
            "class_id": class_1.id,
            "level": class_code,
            "type": "Undergraduate",
            "department_id": dept_b.id,
            "specialization_id": None,
            "academic_year_id": year_1.id,
            "guardian_id": guardian_1.id,
            "created_at": now,
        },
    )
    course_a, _ = _get_or_create(
        db,
        Course,
        {"code": course_a_code},
        {
            "institution_id": tenant.id,
            "name": course_a_name,
            "description": f"{course_a_name} Foundation",
            "department_id": dept_a.id,
            "credits": 3.0,
            "semester": 1,
            "created_at": now,
        },
    )
    course_b, _ = _get_or_create(
        db,
        Course,
        {"code": course_b_code},
        {
            "institution_id": tenant.id,
            "name": course_b_name,
            "description": f"{course_b_name} Foundation",
            "department_id": dept_b.id,
            "credits": 3.0,
            "semester": 1,
            "created_at": now,
        },
    )
    _get_or_create(
        db,
        Enrollment,
        {"institution_id": tenant.id, "student_id": student_1.id, "course_id": course_a.id},
        {"status": "active", "enrollment_date": now, "created_at": now},
    )
    _get_or_create(
        db,
        Enrollment,
        {"institution_id": tenant.id, "student_id": student_1.id, "course_id": course_b.id},
        {"status": "active", "enrollment_date": now, "created_at": now},
    )
    _get_or_create(
        db,
        Schedule,
        {"institution_id": tenant.id, "course_name": course_b.name, "day": schedule_day, "start_time": "09:00"},
        {
            "instructor": f"{teacher_1.firstname} {teacher_1.lastname}",
            "end_time": "11:00",
            "room": "Lab 1",
            "capacity": 80,
            "description": f"Weekly {course_b.name} lecture",
            "created_at": now,
        },
    )
    _get_or_create(
        db,
        Assignment,
        {"institution_id": tenant.id, "course_code": course_b.code, "title": "Intro Project"},
        {
            "description": "Build hello-world app",
            "due_date": (now + timedelta(days=7)).date(),
            "max_score": 20,
            "late_penalty": 10,
            "created_by": "Lecturer",
            "lecturer_id": teacher_1.id,
            "created_at": now,
        },
    )
    _get_or_create(
        db,
        StudentRecord,
        {"institution_id": tenant.id, "student_id": student_1.student_id, "course_code": course_b.code, "semester": "Term 1"},
        {"assignment": 8, "ca": 10, "exam": 65, "total_score": 83, "letter_grade": "B", "gpa": 3.0, "created_at": now},
    )
    _get_or_create(
        db,
        Announcement,
        {"institution_id": tenant.id, "title": "Welcome"},
        {"content": "Welcome to the new academic year.", "target_audience": "all", "created_by": admin_user.id, "created_at": now},
    )
    _get_or_create(
        db,
        Note,
        {"institution_id": tenant.id, "title": f"{course_b.name} Notes"},
        {
            "course_id": course_b.id,
            "course_code": course_b.code,
            "department_id": dept_b.id,
            "lecturer_id": teacher_1.id,
            "content": "Week 1 notes",
            "created_by": admin_user.id,
            "created_at": now,
        },
    )
    _get_or_create(
        db,
        Complaint,
        {"institution_id": tenant.id, "student_id": student_1.student_id, "caption": "Sample complaint"},
        {
            "complaint_type": "academic_record",
            "contents": "This is a seeded complaint",
            "is_anonymous": False,
            "status": "pending",
            "submission_date": now,
            "created_at": now,
        },
    )
    _get_or_create(
        db,
        Activity,
        {"institution_id": tenant.id, "action": "Seeded data", "entity_type": "system"},
        {
            "entity_id": None,
            "performed_by": "Seeder",
            "performer_role": "system_admin",
            "performer_id": admin_user.id,
            "content": f"Initial dataset populated for {tenant_name}",
            "created_at": now,
        },
    )


def run_seed() -> None:
    db = DefaultSessionLocal()
    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        print("[seed] Starting comprehensive relational seed...")

        _seed_tenant_bundle(
            db,
            now=now,
            tenant_name="Demo Academy",
            tenant_domain="demoacademy",
            tenant_category="HI",
            branch_name="Main Campus",
            dept_a_name="Mathematics",
            dept_a_code_suffix="MATH",
            dept_b_name="Computer Science",
            dept_b_code_suffix="CS",
            class_code="L100",
            class_name="Level 100",
            class_level="HI",
            guardian_phone="+237600000001",
            guardian_name="Jane Parent",
            teacher_firstname="John",
            teacher_lastname="Lecturer",
            teacher_email_local="lecturer",
            teacher_phone="+237600000002",
            teacher_employee_id="EMP_DEMO_001",
            student_reg="STU_DEMO_001",
            student_firstname="Alice",
            student_lastname="Learner",
            student_email_local="student",
            student_phone="+237600000004",
            course_a_code="MATH101_DEMO",
            course_a_name="Mathematics 101",
            course_b_code="CS101_DEMO",
            course_b_name="Computer Science 101",
            schedule_day="Monday",
        )

        _seed_tenant_bundle(
            db,
            now=now,
            tenant_name="Riggs Secondary",
            tenant_domain="riggssecondary",
            tenant_category="SI",
            branch_name="Central Campus",
            dept_a_name="Science",
            dept_a_code_suffix="SCI",
            dept_b_name="Arts",
            dept_b_code_suffix="ART",
            class_code="F1",
            class_name="Form 1",
            class_level="SI",
            guardian_phone="+237600000101",
            guardian_name="Mary Guardian",
            teacher_firstname="Grace",
            teacher_lastname="Tutor",
            teacher_email_local="tutor",
            teacher_phone="+237600000102",
            teacher_employee_id="EMP_RIGGS_001",
            student_reg="STU_RIGGS_001",
            student_firstname="Brian",
            student_lastname="Student",
            student_email_local="learner",
            student_phone="+237600000103",
            course_a_code="SCI101_RIGGS",
            course_a_name="Integrated Science",
            course_b_code="ART101_RIGGS",
            course_b_name="Creative Arts",
            schedule_day="Tuesday",
        )

        db.commit()
        print("[seed] Complete. Multi-tenant core tables populated with valid relationships.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
