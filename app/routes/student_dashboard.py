import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from fastapi import HTTPException
from fastapi import Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user_tenant
from app.dependencies.auth import require_any_role
from app.dependencies.tenantDependency import get_db
from app.apis.students import resolve_student_for_logged_in_user
from app.models.announcement import Announcement
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.note import Note
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.student_record import StudentRecord
from app.models.academic_year import AcademicYear
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import UserRole
from app.models.student_attendance_entry import StudentAttendanceEntry
from app.models.student_chat import StudentChatThread, StudentChatMessage
from app.models.teacher import Teacher
from app.models.communication import Communication
from app.helpers.user_roles import user_has_any_role
from app.schemas.ranking import RankingRecomputeRequest, RankingRecomputeResponse
from app.services.ranking_jobs import enqueue_rank_recompute
from app.services.ranking_service import (
    build_overview_rankings_payload,
    get_course_rank_rows,
    get_student_course_rank_rows,
    rank_classes,
    rank_schools,
    rank_students_overall,
)

router = APIRouter(prefix="/student-dashboard", tags=["student-dashboard"])
logger = logging.getLogger(__name__)


def _raise_chat_thread_db_error(db: Session, exc: Exception) -> None:
    """Map common DB/schema failures to a clear API error instead of HTTP 500."""
    db.rollback()
    raw = str(getattr(exc, "orig", exc) or exc)
    lowered = raw.lower()
    if (
        "unknown column" in lowered
        or "1054" in raw  # MySQL unknown column
        or "does not exist" in lowered  # PostgreSQL undefined column / relation
        or "no such column" in lowered  # SQLite
        or "direct_peer_matricule" in lowered
        or "counterpart_user_id" in lowered
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "Student chat database schema is outdated. Apply Alembic migrations "
                "for this tenant database (revision 20260517_stu_chat_dm: adds "
                "student_chat_threads.counterpart_user_id and direct_peer_matricule), "
                "then retry. Command: alembic upgrade head"
            ),
        ) from None
    raise exc


def _resolve_student(db: Session, current_user: User) -> Optional[Student]:
    return resolve_student_for_logged_in_user(db, current_user)


def _grade_to_points(letter_grade: Optional[str]) -> float:
    points = {
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D": 1.0,
        "F": 0.0,
    }
    return points.get((letter_grade or "").upper().strip(), 0.0)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_academic_year_label(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = str(value).strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) >= 8:
        start_year = digits[:4]
        end_year = digits[4:8]
        return f"{start_year[-2:]}/{end_year[-2:]}"
    if len(digits) >= 4:
        start = int(digits[:4])
        return f"{str(start)[-2:]}/{str(start + 1)[-2:]}"
    return raw


def _build_rankings_payload_for_student(
    db: Session,
    institution_id: int,
    student_id: str,
    tenant_category: Optional[str],
    top_n: int = 3,
) -> Dict[str, Any]:
    student_top = rank_students_overall(db=db, institution_id=institution_id, top_n=top_n)
    class_top = rank_classes(db=db, institution_id=institution_id, top_n=top_n)
    school_top = rank_schools(db=db, institution_id=institution_id, top_n=top_n)
    course_ranks = get_student_course_rank_rows(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
    )
    current_student_item = next((item for item in student_top if str(item["student_id"]) == str(student_id)), None)
    current_student = {
        "student_id": str(student_id),
        "course_ranks": course_ranks,
        "class_rank": current_student_item["rank"] if current_student_item else None,
        "school_rank": current_student_item["rank"] if current_student_item else None,
    }
    return {
        "rankings": {
            "students": {"top3": student_top},
            "classes": {"top3": class_top},
            "schools": {"top3": school_top},
            "course": course_ranks,
            "current_student": current_student if str(tenant_category or "").upper() == "SI" else None,
        },
        "meta": {
            "tenant_category": tenant_category,
            "scope": "institution",
            "top_n": top_n,
            "computed_at": datetime.utcnow().isoformat(),
        },
    }


@router.get("/context")
def get_student_dashboard_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    institution_id = current_user.institution_id
    if not institution_id:
        return {"tenant_category": None, "academic_year": None}

    tenant = (
        db.query(Tenant)
        .filter(Tenant.id == institution_id)
        .first()
    )
    tenant_category = tenant.category if tenant else None

    current_year = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
            AcademicYear.is_current.is_(True),
        )
        .order_by(AcademicYear.updated_at.desc(), AcademicYear.id.desc())
        .first()
    )
    if not current_year:
        current_year = (
            db.query(AcademicYear)
            .filter(
                AcademicYear.institution_id == institution_id,
                AcademicYear.deleted_at.is_(None),
            )
            .order_by(AcademicYear.updated_at.desc(), AcademicYear.id.desc())
            .first()
        )
    academic_year = _format_academic_year_label(current_year.name if current_year else None)
    return {
        "tenant_category": tenant_category,
        "academic_year": academic_year,
    }


@router.get("/overview")
def get_student_dashboard_overview(
    view_mode: str = Query("today", pattern="^(today|weekly|action_required)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"view_mode": view_mode, "next_actions": [], "items": []}

    today = datetime.utcnow().date()
    next_week = today + timedelta(days=7)

    assignments_q = (
        db.query(Assignment)
        .filter(
            Assignment.institution_id == student.institution_id,
            Assignment.deleted_at.is_(None),
        )
        .order_by(Assignment.due_date.asc())
    )
    if view_mode == "today":
        assignments_q = assignments_q.filter(Assignment.due_date == today)
    elif view_mode == "weekly":
        assignments_q = assignments_q.filter(Assignment.due_date >= today, Assignment.due_date <= next_week)
    else:
        assignments_q = assignments_q.filter(Assignment.due_date <= next_week)

    assignments = assignments_q.limit(20).all()
    records = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.institution_id == student.institution_id,
            StudentRecord.student_id == student.student_id,
            StudentRecord.deleted_at.is_(None),
        )
        .order_by(StudentRecord.created_at.desc())
        .limit(20)
        .all()
    )

    submissions = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.institution_id == student.institution_id,
            AssignmentSubmission.student_id == student.student_id,
            AssignmentSubmission.deleted_at.is_(None),
        )
        .all()
    )
    submitted_assignment_ids = {s.assignment_id for s in submissions}

    next_actions: List[Dict[str, Any]] = []
    for assignment in assignments:
        is_submitted = assignment.id in submitted_assignment_ids
        if not is_submitted:
            next_actions.append(
                {
                    "type": "submit_assignment",
                    "priority": "high" if assignment.due_date and assignment.due_date <= today + timedelta(days=1) else "medium",
                    "title": f"Submit {assignment.title}",
                    "course_code": assignment.course_code,
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "path": "/assignments",
                }
            )

    for record in records[:5]:
        if _safe_float(record.total_score) < 50:
            next_actions.append(
                {
                    "type": "improve_grade",
                    "priority": "medium",
                    "title": f"Review weak performance in {record.course_code}",
                    "course_code": record.course_code,
                    "path": "/academics",
                }
            )

    items = [
        {
            "id": a.id,
            "kind": "assignment",
            "title": a.title,
            "course_code": a.course_code,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "status": "submitted" if a.id in submitted_assignment_ids else "pending",
        }
        for a in assignments
    ]
    return {"view_mode": view_mode, "next_actions": next_actions[:8], "items": items}


@router.get("/history")
def get_student_academic_history(
    course_code: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    query = db.query(StudentRecord).filter(
        StudentRecord.institution_id == student.institution_id,
        StudentRecord.student_id == student.student_id,
        StudentRecord.deleted_at.is_(None),
    )
    if course_code:
        query = query.filter(StudentRecord.course_code == course_code)
    if semester:
        query = query.filter(StudentRecord.semester == semester)
    if status == "pass":
        query = query.filter(StudentRecord.letter_grade.in_(["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D"]))
    elif status == "fail":
        query = query.filter(StudentRecord.letter_grade == "F")

    total = query.count()
    records = (
        query.order_by(StudentRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": r.id,
            "course_code": r.course_code,
            "semester": r.semester,
            "assignment": _safe_float(r.assignment),
            "ca": _safe_float(r.ca),
            "exam": _safe_float(r.exam),
            "total_score": _safe_float(r.total_score),
            "letter_grade": r.letter_grade,
            "gpa": _safe_float(r.gpa),
            "status": "pass" if r.letter_grade in {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D"} else "fail",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/grades")
def get_student_grades(
    course_code: Optional[str] = Query(None),
    semester: Optional[str] = Query(None),
    academic_year: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "summary": {"gpa": 0.0, "average_score": 0.0, "record_count": 0},
        }

    enrolled_courses = (
        db.query(Course)
        .join(
            Enrollment,
            (Enrollment.course_id == Course.id)
            & (Enrollment.institution_id == student.institution_id)
            & (Enrollment.student_id == student.id)
            & (Enrollment.deleted_at.is_(None))
            & (Enrollment.status.in_(["active", "completed"])),
        )
        .filter(
            Course.institution_id == student.institution_id,
            Course.deleted_at.is_(None),
        )
        .all()
    )
    course_by_code = {course.code: course for course in enrolled_courses if course.code}
    enrolled_course_codes = list(course_by_code.keys())

    current_year = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == student.institution_id,
            AcademicYear.deleted_at.is_(None),
            AcademicYear.is_current.is_(True),
        )
        .order_by(AcademicYear.updated_at.desc(), AcademicYear.id.desc())
        .first()
    )
    if not current_year:
        current_year = (
            db.query(AcademicYear)
            .filter(
                AcademicYear.institution_id == student.institution_id,
                AcademicYear.deleted_at.is_(None),
            )
            .order_by(AcademicYear.updated_at.desc(), AcademicYear.id.desc())
            .first()
        )
    current_academic_year = current_year.name if current_year and current_year.name else None

    query = db.query(StudentRecord).filter(
        StudentRecord.institution_id == student.institution_id,
        StudentRecord.student_id == student.student_id,
        StudentRecord.deleted_at.is_(None),
    )
    if enrolled_course_codes:
        query = query.filter(StudentRecord.course_code.in_(enrolled_course_codes))
    if course_code:
        query = query.filter(StudentRecord.course_code == course_code)
    if semester:
        query = query.filter(StudentRecord.semester == semester)
    if academic_year:
        if current_academic_year and academic_year == current_academic_year:
            query = query.filter(or_(StudentRecord.academic_year == academic_year, StudentRecord.academic_year.is_(None)))
        else:
            query = query.filter(StudentRecord.academic_year == academic_year)

    total = query.count()
    summary_records = query.all()
    record_count = len(summary_records)
    average_score = round(sum(_safe_float(r.total_score) for r in summary_records) / record_count, 2) if record_count else 0.0
    gpa = round(sum(_safe_float(r.gpa) for r in summary_records) / record_count, 2) if record_count else 0.0

    records = (
        query.order_by(StudentRecord.created_at.desc(), StudentRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "course_code": r.course_code,
                "course_name": course_by_code.get(r.course_code).name if course_by_code.get(r.course_code) else r.course_code,
                "academic_year": r.academic_year or current_academic_year,
                "semester": r.semester,
                "assignment": _safe_float(r.assignment),
                "ca": _safe_float(r.ca),
                "exam": _safe_float(r.exam),
                "total_score": _safe_float(r.total_score),
                "letter_grade": r.letter_grade,
                "gpa": _safe_float(r.gpa),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": {"gpa": gpa, "average_score": average_score, "record_count": record_count},
    }


@router.get("/analytics")
def get_student_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"gpa_trend": [], "grade_context": [], "strengths": [], "weaknesses": [], "rankings": {}}

    records = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.institution_id == student.institution_id,
            StudentRecord.student_id == student.student_id,
            StudentRecord.deleted_at.is_(None),
        )
        .order_by(StudentRecord.created_at.asc())
        .all()
    )
    if not records:
        return {"gpa_trend": [], "grade_context": [], "strengths": [], "weaknesses": [], "rankings": {}}

    tenant = db.query(Tenant).filter(Tenant.id == student.institution_id).first()
    tenant_category = tenant.category if tenant else None
    rankings_payload = _build_rankings_payload_for_student(
        db=db,
        institution_id=student.institution_id,
        student_id=student.student_id,
        tenant_category=tenant_category,
    )

    course_scores: Dict[str, List[float]] = {}
    for r in records:
        course_scores.setdefault(r.course_code, []).append(_safe_float(r.total_score))

    strengths = sorted(
        [{"course_code": code, "avg_score": sum(scores) / len(scores)} for code, scores in course_scores.items()],
        key=lambda x: x["avg_score"],
        reverse=True,
    )[:3]
    weaknesses = sorted(
        [{"course_code": code, "avg_score": sum(scores) / len(scores)} for code, scores in course_scores.items()],
        key=lambda x: x["avg_score"],
    )[:3]

    grade_context: List[Dict[str, Any]] = []
    for r in records[-10:]:
        class_avg = (
            db.query(func.avg(StudentRecord.total_score))
            .filter(
                StudentRecord.institution_id == student.institution_id,
                StudentRecord.course_code == r.course_code,
                StudentRecord.deleted_at.is_(None),
            )
            .scalar()
        )
        class_avg_float = _safe_float(class_avg)
        score = _safe_float(r.total_score)
        grade_context.append(
            {
                "course_code": r.course_code,
                "score": score,
                "class_average": round(class_avg_float, 2),
                "student_delta": round(score - class_avg_float, 2),
                "trend_direction": "up" if score >= class_avg_float else "down",
                "letter_grade": r.letter_grade,
            }
        )

    gpa_trend = []
    running_points = 0.0
    for idx, r in enumerate(records, start=1):
        running_points += _grade_to_points(r.letter_grade)
        gpa_trend.append(
            {
                "index": idx,
                "course_code": r.course_code,
                "semester": r.semester,
                "gpa": round(running_points / idx, 2),
            }
        )

    return {
        "gpa_trend": gpa_trend[-12:],
        "grade_context": grade_context,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "rankings": rankings_payload["rankings"],
        "rankings_meta": rankings_payload["meta"],
    }


@router.get("/alerts")
def get_student_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"alerts": []}

    alerts: List[Dict[str, Any]] = []
    records = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.institution_id == student.institution_id,
            StudentRecord.student_id == student.student_id,
            StudentRecord.deleted_at.is_(None),
        )
        .order_by(StudentRecord.created_at.desc())
        .limit(10)
        .all()
    )
    low_scores = [r for r in records if _safe_float(r.total_score) < 50]
    if len(low_scores) >= 2:
        alerts.append(
            {
                "id": "low_performance_pattern",
                "severity": "high",
                "reason": "Multiple recent low scores detected",
                "suggested_action": "Review weak courses and book support session",
                "path": "/academics",
            }
        )

    upcoming_due = (
        db.query(Assignment)
        .filter(
            Assignment.institution_id == student.institution_id,
            Assignment.deleted_at.is_(None),
            Assignment.due_date >= date.today(),
            Assignment.due_date <= date.today() + timedelta(days=2),
        )
        .count()
    )
    if upcoming_due > 0:
        alerts.append(
            {
                "id": "upcoming_deadline",
                "severity": "medium",
                "reason": f"{upcoming_due} assignment(s) due within 48 hours",
                "suggested_action": "Open assignments and submit pending work",
                "path": "/assignments",
            }
        )
    return {"alerts": alerts}


@router.get("/search")
def search_student_dashboard(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"items": []}

    q_like = f"%{q.strip()}%"
    results: List[Dict[str, Any]] = []

    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.institution_id == student.institution_id,
            Assignment.deleted_at.is_(None),
            (Assignment.title.ilike(q_like) | Assignment.course_code.ilike(q_like)),
        )
        .limit(limit)
        .all()
    )
    for a in assignments:
        results.append({"type": "assignment", "title": a.title, "subtitle": a.course_code, "path": "/assignments"})

    notes = (
        db.query(Note)
        .filter(
            Note.institution_id == student.institution_id,
            Note.deleted_at.is_(None),
            (Note.title.ilike(q_like) | Note.content.ilike(q_like)),
        )
        .limit(limit)
        .all()
    )
    for n in notes:
        results.append({"type": "note", "title": n.title, "subtitle": n.course_name or "", "path": "/notes"})

    courses = (
        db.query(Course)
        .filter(
            Course.institution_id == student.institution_id,
            Course.deleted_at.is_(None),
            (Course.name.ilike(q_like) | Course.code.ilike(q_like)),
        )
        .limit(limit)
        .all()
    )
    for c in courses:
        results.append({"type": "course", "title": c.name, "subtitle": c.code, "path": "/my-courses"})

    return {"items": results[:limit]}


@router.get("/export/performance-summary")
def export_performance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"generated_at": datetime.utcnow().isoformat(), "student": None, "summary": {}, "records": [], "rankings": {}}

    records = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.institution_id == student.institution_id,
            StudentRecord.student_id == student.student_id,
            StudentRecord.deleted_at.is_(None),
        )
        .all()
    )
    avg_score = round(sum(_safe_float(r.total_score) for r in records) / len(records), 2) if records else 0.0
    avg_gpa = round(sum(_safe_float(r.gpa) for r in records) / len(records), 2) if records else 0.0
    tenant = db.query(Tenant).filter(Tenant.id == student.institution_id).first()
    tenant_category = tenant.category if tenant else None
    rankings_payload = _build_rankings_payload_for_student(
        db=db,
        institution_id=student.institution_id,
        student_id=student.student_id,
        tenant_category=tenant_category,
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "student": {
            "student_id": student.student_id,
            "name": f"{student.firstname or ''} {student.lastname or ''}".strip(),
            "email": student.email,
        },
        "summary": {
            "record_count": len(records),
            "average_score": avg_score,
            "average_gpa": avg_gpa,
        },
        "records": [
            {
                "course_code": r.course_code,
                "semester": r.semester,
                "total_score": _safe_float(r.total_score),
                "letter_grade": r.letter_grade,
                "gpa": _safe_float(r.gpa),
            }
            for r in records
        ],
        "rankings": rankings_payload["rankings"],
        "rankings_meta": rankings_payload["meta"],
    }


@router.get("/rankings/overview")
def get_rankings_overview(
    top_n: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    institution_id = current_user.institution_id
    if not institution_id:
        return {"rankings": {"students": {"top3": []}, "classes": {"top3": []}, "schools": {"top3": []}}, "meta": {"top_n": top_n}}
    tenant = db.query(Tenant).filter(Tenant.id == institution_id).first()
    tenant_category = tenant.category if tenant else None
    payload = build_overview_rankings_payload(db=db, institution_id=institution_id, top_n=top_n)
    return {
        "rankings": payload,
        "meta": {
            "tenant_category": tenant_category,
            "scope": "institution",
            "top_n": top_n,
            "computed_at": datetime.utcnow().isoformat(),
        },
    }


@router.get("/rankings/course")
def get_rankings_for_course(
    course_code: str = Query(..., min_length=1),
    academic_year: Optional[str] = Query(None),
    semester_or_term: Optional[str] = Query(None),
    top_n: int = Query(0, ge=0, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    institution_id = current_user.institution_id
    if not institution_id:
        return {"items": [], "meta": {"course_code": course_code}}
    rows = get_course_rank_rows(
        db=db,
        institution_id=institution_id,
        course_code=course_code,
        academic_year=academic_year,
        semester_or_term=semester_or_term,
        top_n=top_n or None,
    )
    return {
        "items": rows,
        "meta": {
            "course_code": course_code,
            "academic_year": academic_year,
            "semester_or_term": semester_or_term,
            "top_n": top_n,
            "count": len(rows),
        },
    }


@router.post("/rankings/recompute", response_model=RankingRecomputeResponse)
def post_rankings_recompute(
    request: RankingRecomputeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN)),
):
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="Institution scope is required")
    result = enqueue_rank_recompute(
        institution_id=institution_id,
        course_code=request.course_code,
        academic_year=request.academic_year,
        semester_or_term=request.semester_or_term,
        reason="manual_backfill",
    )
    return RankingRecomputeResponse(status=result["status"], correlation_id=result["correlation_id"])


@router.get("/semesters")
def get_student_dashboard_semesters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return []
    semesters = (
        db.query(StudentRecord.semester)
        .filter(
            StudentRecord.institution_id == student.institution_id,
            StudentRecord.student_id == student.student_id,
            StudentRecord.deleted_at.is_(None),
            StudentRecord.semester.isnot(None),
        )
        .distinct()
        .order_by(StudentRecord.semester)
        .all()
    )
    return [s.semester for s in semesters if s.semester]


@router.get("/academic-years")
def get_student_dashboard_academic_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        institution_id = current_user.institution_id if current_user else None
        if not institution_id:
            return []
    else:
        institution_id = student.institution_id

    years = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .order_by(AcademicYear.name.asc())
        .all()
    )
    options = {str(y.name): {"id": y.id, "name": y.name} for y in years if y.name}

    if student:
        record_years = (
            db.query(StudentRecord.academic_year)
            .filter(
                StudentRecord.institution_id == student.institution_id,
                StudentRecord.student_id == student.student_id,
                StudentRecord.deleted_at.is_(None),
                StudentRecord.academic_year.isnot(None),
            )
            .distinct()
            .order_by(StudentRecord.academic_year.asc())
            .all()
        )
        for row in record_years:
            if row.academic_year and str(row.academic_year) not in options:
                options[str(row.academic_year)] = {"id": str(row.academic_year), "name": str(row.academic_year)}

    return list(options.values())


def _enrolled_course_codes(db: Session, student: Student) -> List[str]:
    rows = (
        db.query(Course.code)
        .join(
            Enrollment,
            (Enrollment.course_id == Course.id)
            & (Enrollment.institution_id == student.institution_id)
            & (Enrollment.student_id == student.id)
            & (Enrollment.deleted_at.is_(None))
            & (Enrollment.status.in_(["active", "completed"])),
        )
        .filter(Course.institution_id == student.institution_id, Course.deleted_at.is_(None))
        .all()
    )
    return [r.code for r in rows if r.code]


def _user_is_staffish(user: User) -> bool:
    return user_has_any_role(
        user,
        [
            UserRole.ADMIN.value,
            UserRole.STAFF.value,
            UserRole.SUPER_ADMIN.value,
            UserRole.SECRETARY.value,
        ],
    )


def _communication_applies_to_student(comm: Communication, student: Student) -> bool:
    rf = comm.recipient_filter or {}
    rtype = (comm.recipient_type or "").lower()
    if rtype == "individual":
        ids = rf.get("student_ids") or rf.get("matricules") or []
        emails = rf.get("emails") or []
        sid_match = str(student.student_id) in {str(x) for x in ids} if ids else False
        email_match = student.email in {str(x).lower() for x in emails} if emails else False
        return sid_match or email_match
    if rtype == "role":
        roles = rf.get("roles")
        if not roles:
            return True
        if not isinstance(roles, list):
            roles = [roles]
        lowered = {str(x).lower() for x in roles}
        return bool(lowered & {"student", "students", "all", "everyone"})
    if rtype == "class":
        return rf.get("class_id") == student.class_id
    if rtype == "department":
        return rf.get("department_id") == student.department_id
    return False


def _normalize_peer_matricules(m1: str, m2: str) -> tuple[str, str]:
    a = (m1 or "").strip()
    b = (m2 or "").strip()
    return (a, b) if a <= b else (b, a)


def _user_is_messaging_staff_contact(u: User) -> bool:
    return user_has_any_role(u, ["admin", "super_admin", "secretary", "staff", "teacher"])


def _user_may_override_directed_staff_thread(u: User) -> bool:
    return user_has_any_role(u, ["admin", "super_admin"])


def _user_id_for_student_record(db: Session, inst_id: int, st: Student) -> Optional[int]:
    if not st or not inst_id:
        return None
    email_norm = (st.email or "").strip()
    if email_norm:
        row = (
            db.query(User.id)
            .filter(
                User.institution_id == inst_id,
                User.deleted_at.is_(None),
                func.lower(User.email) == email_norm.lower(),
            )
            .first()
        )
        if row:
            return int(row[0])
    sid = (st.student_id or "").strip()
    if sid:
        row = (
            db.query(User.id)
            .filter(
                User.institution_id == inst_id,
                User.deleted_at.is_(None),
                User.username == sid,
            )
            .first()
        )
        if row:
            return int(row[0])
        row = (
            db.query(User.id)
            .filter(
                User.institution_id == inst_id,
                User.deleted_at.is_(None),
                func.lower(User.email) == sid.lower(),
            )
            .first()
        )
        if row:
            return int(row[0])
    return None


def _human_label_for_user(u: User) -> str:
    name = f"{(u.firstname or '').strip()} {(u.lastname or '').strip()}".strip()
    return name or (u.email or u.username or f"User #{u.id}")


def _staff_thread_visible_to_user(thread: StudentChatThread, user: User) -> bool:
    if (thread.kind or "").lower() != "staff":
        return True
    target = getattr(thread, "counterpart_user_id", None)
    if not target:
        return True
    if int(target) == int(user.id):
        return True
    return _user_may_override_directed_staff_thread(user)


def _user_can_access_thread(
    db: Session,
    thread: StudentChatThread,
    current_user: User,
    student: Optional[Student],
) -> bool:
    if thread.institution_id != (current_user.institution_id or 0):
        return False
    if thread.deleted_at is not None:
        return False
    if _user_is_staffish(current_user):
        if (thread.kind or "").lower() == "direct":
            return False
        if (thread.kind or "").lower() == "staff":
            return _staff_thread_visible_to_user(thread, current_user)
        return True
    if not student:
        return False
    k = (thread.kind or "").lower()
    if k == "staff":
        return (thread.student_owner_matricule or "") == str(student.student_id)
    if k == "course":
        codes = _enrolled_course_codes(db, student)
        return bool(thread.course_code and thread.course_code in codes)
    if k == "direct":
        mine = str(student.student_id).strip()
        a = (thread.student_owner_matricule or "").strip()
        b = (thread.direct_peer_matricule or "").strip()
        return bool(a and b and mine in {a, b})
    return False


class AttendanceEntryCreate(BaseModel):
    student_id: str = Field(..., min_length=1)
    course_code: str = Field(..., min_length=1)
    session_date: date
    status: str = Field("present", pattern="^(present|absent|late|excused)$")
    notes: Optional[str] = None


class ChatThreadCreate(BaseModel):
    kind: str = Field(..., pattern="^(staff|course|direct)$")
    course_code: Optional[str] = None
    title: Optional[str] = None
    staff_user_id: Optional[int] = None
    peer_user_id: Optional[int] = None


class ChatMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)
    parent_message_id: Optional[int] = None


@router.get("/attendance/summary")
def get_student_attendance_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "percentage": 0.0,
            "total_sessions": 0,
        }
    q = (
        db.query(StudentAttendanceEntry)
        .filter(
            StudentAttendanceEntry.institution_id == student.institution_id,
            StudentAttendanceEntry.student_id == student.student_id,
            StudentAttendanceEntry.deleted_at.is_(None),
        )
    )
    rows = q.all()
    present = sum(1 for r in rows if (r.status or "").lower() == "present")
    absent = sum(1 for r in rows if (r.status or "").lower() == "absent")
    late = sum(1 for r in rows if (r.status or "").lower() == "late")
    excused = sum(1 for r in rows if (r.status or "").lower() == "excused")
    total = len(rows)
    # Treat late as attended for percentage
    attended = present + late + excused
    pct = round((attended / total) * 100, 1) if total else 0.0
    return {
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "percentage": pct,
        "total_sessions": total,
    }


@router.get("/attendance/records")
def get_student_attendance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    q = (
        db.query(StudentAttendanceEntry)
        .filter(
            StudentAttendanceEntry.institution_id == student.institution_id,
            StudentAttendanceEntry.student_id == student.student_id,
            StudentAttendanceEntry.deleted_at.is_(None),
        )
    )
    total = q.count()
    records = (
        q.order_by(StudentAttendanceEntry.session_date.desc(), StudentAttendanceEntry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": r.id,
            "course_code": r.course_code,
            "session_date": r.session_date.isoformat() if r.session_date else None,
            "status": r.status,
            "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/attendance/entries")
def create_student_attendance_entry(
    payload: AttendanceEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.TEACHER, UserRole.SUPER_ADMIN, UserRole.SECRETARY)),
):
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="Institution required")
    row = StudentAttendanceEntry(
        institution_id=current_user.institution_id,
        student_id=payload.student_id.strip(),
        course_code=payload.course_code.strip(),
        session_date=payload.session_date,
        status=payload.status,
        notes=payload.notes,
        recorded_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "message": "Recorded"}


@router.get("/communications/inbox")
def list_student_communication_inbox(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        return {"items": []}
    comms = (
        db.query(Communication)
        .filter(
            Communication.institution_id == student.institution_id,
            Communication.deleted_at.is_(None),
        )
        .order_by(Communication.created_at.desc())
        .limit(200)
        .all()
    )
    visible: List[Communication] = [c for c in comms if _communication_applies_to_student(c, student)]
    visible = visible[:limit]
    sender_ids = {c.sender_id for c in visible}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(sender_ids)).all()} if sender_ids else {}
    items = []
    for c in visible:
        u = users.get(c.sender_id)
        sender_label = (
            f"{(u.firstname or '').strip()} {(u.lastname or '').strip()}".strip() if u else f"User #{c.sender_id}"
        )
        items.append(
            {
                "id": c.id,
                "channel": c.channel,
                "subject": c.subject,
                "content": c.content,
                "recipient_type": c.recipient_type,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "sender_label": sender_label,
            }
        )
    return {"items": items}


def _student_display_name(st: Student) -> str:
    parts = [st.firstname or "", st.middlename or "", st.lastname or ""]
    name = " ".join(p for p in parts if p).strip()
    return name or (st.email or st.student_id or "Student")


def _thread_list_title(db: Session, t: StudentChatThread, viewer_student: Optional[Student]) -> str:
    k = (t.kind or "").lower()
    if k == "course":
        return t.title or (f"Course: {t.course_code}" if t.course_code else "Course chat")
    if k == "staff":
        if getattr(t, "counterpart_user_id", None):
            cu = db.query(User).filter(User.id == t.counterpart_user_id).first()
            if cu:
                return t.title or f"Staff: {_human_label_for_user(cu)}"
        return t.title or "Staff messages"
    if k == "direct" and viewer_student:
        mine = str(viewer_student.student_id).strip()
        a = (t.student_owner_matricule or "").strip()
        b = (t.direct_peer_matricule or "").strip()
        other_mat = b if mine == a else a if mine == b else ""
        if other_mat:
            other = (
                db.query(Student)
                .filter(
                    Student.institution_id == t.institution_id,
                    Student.student_id == other_mat,
                    Student.deleted_at.is_(None),
                )
                .first()
            )
            if other:
                return f"Chat with {_student_display_name(other)}"
        return "Private chat"
    return t.title or "Messages"


@router.get("/messages/contacts/staff")
def list_staff_message_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        raise HTTPException(status_code=403, detail="Student profile required")
    if not current_user.institution_id:
        return {"items": []}
    rows = (
        db.query(User)
        .filter(
            User.institution_id == current_user.institution_id,
            User.deleted_at.is_(None),
            User.id != current_user.id,
        )
        .order_by(User.lastname.asc(), User.firstname.asc())
        .limit(400)
        .all()
    )
    items = []
    for u in rows:
        if not _user_is_messaging_staff_contact(u):
            continue
        items.append({"user_id": u.id, "label": _human_label_for_user(u)})
    items.sort(key=lambda x: (x["label"] or "").lower())
    return {"items": items}


@router.get("/messages/contacts/course")
def list_course_message_contacts(
    course_code: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        raise HTTPException(status_code=403, detail="Student profile required")
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="Institution required")
    code = (course_code or "").strip()
    codes = _enrolled_course_codes(db, student)
    if code not in codes:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")
    course = (
        db.query(Course)
        .filter(
            Course.institution_id == current_user.institution_id,
            Course.code == code,
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    lecturers: List[Dict[str, Any]] = []
    if course.instructor_id:
        teacher = (
            db.query(Teacher)
            .filter(
                Teacher.id == course.instructor_id,
                Teacher.institution_id == current_user.institution_id,
                Teacher.deleted_at.is_(None),
            )
            .first()
        )
        if teacher and (teacher.email or "").strip():
            email = teacher.email.strip()
            u = (
                db.query(User)
                .filter(
                    User.institution_id == current_user.institution_id,
                    User.deleted_at.is_(None),
                    func.lower(User.email) == email.lower(),
                )
                .first()
            )
            if u and _user_is_messaging_staff_contact(u) and u.id != current_user.id:
                label = f"{_human_label_for_user(u)} (Instructor · {code})"
                lecturers.append({"user_id": u.id, "label": label})

    peer_rows = (
        db.query(Student)
        .join(
            Enrollment,
            (Enrollment.student_id == Student.id)
            & (Enrollment.institution_id == Student.institution_id)
            & (Enrollment.course_id == course.id)
            & (Enrollment.deleted_at.is_(None))
            & (Enrollment.status.in_(["active", "completed"])),
        )
        .filter(
            Student.institution_id == current_user.institution_id,
            Student.deleted_at.is_(None),
            Student.id != student.id,
        )
        .order_by(Student.lastname.asc(), Student.firstname.asc())
        .limit(300)
        .all()
    )
    classmates: List[Dict[str, Any]] = []
    for st in peer_rows:
        uid = _user_id_for_student_record(db, current_user.institution_id, st)
        if not uid or uid == current_user.id:
            continue
        classmates.append(
            {
                "user_id": uid,
                "label": f"{_student_display_name(st)} ({st.student_id})",
                "matricule": st.student_id,
            }
        )
    return {"course_code": code, "lecturers": lecturers, "classmates": classmates}


def _chat_thread_recency_order():
    """Sort by updated_at descending, with NULL updated_at last (MariaDB/MySQL have no NULLS LAST)."""
    return (
        case((StudentChatThread.updated_at.is_(None), 1), else_=0).asc(),
        StudentChatThread.updated_at.desc(),
        StudentChatThread.id.desc(),
    )


@router.get("/messages/threads")
def list_student_chat_threads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    if not current_user.institution_id:
        return {"items": []}
    student = _resolve_student(db, current_user)
    q = db.query(StudentChatThread).filter(
        StudentChatThread.institution_id == current_user.institution_id,
        StudentChatThread.deleted_at.is_(None),
    )
    if _user_is_staffish(current_user):
        q = q.filter(StudentChatThread.kind != "direct")
        if not _user_may_override_directed_staff_thread(current_user):
            q = q.filter(
                or_(
                    StudentChatThread.kind == "course",
                    and_(
                        StudentChatThread.kind == "staff",
                        or_(
                            StudentChatThread.counterpart_user_id.is_(None),
                            StudentChatThread.counterpart_user_id == current_user.id,
                        ),
                    ),
                )
            )
        threads = q.order_by(*_chat_thread_recency_order()).limit(200).all()
    else:
        if not student:
            return {"items": []}
        codes = _enrolled_course_codes(db, student)
        mine = str(student.student_id)
        threads = (
            q.filter(
                or_(
                    and_(StudentChatThread.kind == "staff", StudentChatThread.student_owner_matricule == mine),
                    and_(StudentChatThread.kind == "course", StudentChatThread.course_code.in_(codes)),
                    and_(
                        StudentChatThread.kind == "direct",
                        or_(
                            StudentChatThread.student_owner_matricule == mine,
                            StudentChatThread.direct_peer_matricule == mine,
                        ),
                    ),
                )
            )
            .order_by(*_chat_thread_recency_order())
            .all()
        )
    items = []
    for t in threads:
        items.append(
            {
                "id": t.id,
                "kind": t.kind,
                "course_code": t.course_code,
                "title": _thread_list_title(db, t, student if not _user_is_staffish(current_user) else None),
                "student_owner_matricule": t.student_owner_matricule,
                "direct_peer_matricule": getattr(t, "direct_peer_matricule", None),
                "counterpart_user_id": getattr(t, "counterpart_user_id", None),
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        )
    return {"items": items}


@router.post("/messages/threads", status_code=201)
def create_student_chat_thread(
    payload: ChatThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    student = _resolve_student(db, current_user)
    if not student:
        raise HTTPException(status_code=403, detail="Student profile required")
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="Institution required")
    kind = (payload.kind or "").lower()
    try:
        if kind == "staff":
            staff_uid = payload.staff_user_id
            if not staff_uid:
                raise HTTPException(status_code=400, detail="staff_user_id is required — select a staff member")
            staff_user = (
                db.query(User)
                .filter(
                    User.id == int(staff_uid),
                    User.institution_id == current_user.institution_id,
                    User.deleted_at.is_(None),
                )
                .first()
            )
            if not staff_user or not _user_is_messaging_staff_contact(staff_user):
                raise HTTPException(status_code=400, detail="Invalid staff contact")
            if int(staff_user.id) == int(current_user.id):
                raise HTTPException(status_code=400, detail="Cannot message yourself")
            title = (payload.title or "").strip() or f"Message to {_human_label_for_user(staff_user)}"
            existing = (
                db.query(StudentChatThread)
                .filter(
                    StudentChatThread.institution_id == current_user.institution_id,
                    StudentChatThread.kind == "staff",
                    StudentChatThread.student_owner_matricule == str(student.student_id),
                    StudentChatThread.counterpart_user_id == int(staff_uid),
                    StudentChatThread.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                return {"id": existing.id, "kind": existing.kind, "title": existing.title, "existing": True}
            thread = StudentChatThread(
                institution_id=current_user.institution_id,
                kind="staff",
                course_code=None,
                student_owner_matricule=str(student.student_id),
                direct_peer_matricule=None,
                counterpart_user_id=int(staff_uid),
                title=title,
                created_by_user_id=current_user.id,
            )
            db.add(thread)
            db.commit()
            db.refresh(thread)
            return {"id": thread.id, "kind": thread.kind, "title": thread.title}
        if kind == "course":
            code = (payload.course_code or "").strip()
            if not code:
                raise HTTPException(status_code=400, detail="course_code is required for course threads")
            codes = _enrolled_course_codes(db, student)
            if code not in codes:
                raise HTTPException(status_code=403, detail="Not enrolled in this course")
            existing = (
                db.query(StudentChatThread)
                .filter(
                    StudentChatThread.institution_id == current_user.institution_id,
                    StudentChatThread.kind == "course",
                    StudentChatThread.course_code == code,
                    StudentChatThread.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                return {"id": existing.id, "kind": existing.kind, "title": existing.title, "existing": True}
            course = (
                db.query(Course)
                .filter(
                    Course.institution_id == current_user.institution_id,
                    Course.code == code,
                    Course.deleted_at.is_(None),
                )
                .first()
            )
            cname = course.name if course else code
            thread = StudentChatThread(
                institution_id=current_user.institution_id,
                kind="course",
                course_code=code,
                student_owner_matricule=None,
                direct_peer_matricule=None,
                counterpart_user_id=None,
                title=f"{cname} ({code})",
                created_by_user_id=current_user.id,
            )
            db.add(thread)
            db.commit()
            db.refresh(thread)
            return {"id": thread.id, "kind": thread.kind, "title": thread.title}
        if kind == "direct":
            code = (payload.course_code or "").strip()
            peer_uid = payload.peer_user_id
            if not code or not peer_uid:
                raise HTTPException(status_code=400, detail="course_code and peer_user_id are required for direct chats")
            if int(peer_uid) == int(current_user.id):
                raise HTTPException(status_code=400, detail="Cannot start a chat with yourself")
            codes = _enrolled_course_codes(db, student)
            if code not in codes:
                raise HTTPException(status_code=403, detail="Not enrolled in this course")
            peer_user = (
                db.query(User)
                .filter(
                    User.id == int(peer_uid),
                    User.institution_id == current_user.institution_id,
                    User.deleted_at.is_(None),
                )
                .first()
            )
            if not peer_user:
                raise HTTPException(status_code=400, detail="Peer user not found")
            peer_student = resolve_student_for_logged_in_user(db, peer_user)
            if not peer_student:
                raise HTTPException(status_code=400, detail="Private chats are only supported with another student account")
            if peer_student.id == student.id:
                raise HTTPException(status_code=400, detail="Invalid peer")
            peer_codes = _enrolled_course_codes(db, peer_student)
            if code not in peer_codes:
                raise HTTPException(status_code=403, detail="That student is not enrolled in the selected course")
            m_low, m_high = _normalize_peer_matricules(str(student.student_id), str(peer_student.student_id))
            existing = (
                db.query(StudentChatThread)
                .filter(
                    StudentChatThread.institution_id == current_user.institution_id,
                    StudentChatThread.kind == "direct",
                    StudentChatThread.student_owner_matricule == m_low,
                    StudentChatThread.direct_peer_matricule == m_high,
                    StudentChatThread.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                return {"id": existing.id, "kind": existing.kind, "title": existing.title, "existing": True}
            other_label = _student_display_name(peer_student)
            thread = StudentChatThread(
                institution_id=current_user.institution_id,
                kind="direct",
                course_code=code,
                student_owner_matricule=m_low,
                direct_peer_matricule=m_high,
                counterpart_user_id=None,
                title=f"Chat with {other_label}",
                created_by_user_id=current_user.id,
            )
            db.add(thread)
            db.commit()
            db.refresh(thread)
            return {"id": thread.id, "kind": thread.kind, "title": thread.title}
        raise HTTPException(status_code=400, detail="Invalid kind")
    except HTTPException:
        raise
    except IntegrityError as e:
        logger.warning("create_student_chat_thread integrity error: %s", e)
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create this chat thread (duplicate or invalid reference).",
        ) from None
    except (OperationalError, ProgrammingError) as e:
        logger.warning("create_student_chat_thread database error: %s", e)
        _raise_chat_thread_db_error(db, e)


def _mark_staff_incoming_delivered(db: Session, thread: StudentChatThread, viewer_user_id: int) -> None:
    """Private threads (staff or student-to-student): mark other party's messages delivered when viewer opens the thread."""
    if (thread.kind or "").lower() not in {"staff", "direct"}:
        return
    now = datetime.utcnow()
    db.query(StudentChatMessage).filter(
        StudentChatMessage.thread_id == thread.id,
        StudentChatMessage.deleted_at.is_(None),
        StudentChatMessage.sender_user_id != viewer_user_id,
        StudentChatMessage.delivered_at.is_(None),
    ).update({StudentChatMessage.delivered_at: now}, synchronize_session=False)


def _mark_staff_incoming_read(db: Session, thread: StudentChatThread, viewer_user_id: int) -> int:
    """Mark other party's messages read when viewer opens a private thread."""
    if (thread.kind or "").lower() not in {"staff", "direct"}:
        return 0
    now = datetime.utcnow()
    return int(
        db.query(StudentChatMessage)
        .filter(
            StudentChatMessage.thread_id == thread.id,
            StudentChatMessage.deleted_at.is_(None),
            StudentChatMessage.sender_user_id != viewer_user_id,
            StudentChatMessage.read_at.is_(None),
        )
        .update({StudentChatMessage.read_at: now}, synchronize_session=False)
        or 0
    )


@router.post("/messages/threads/{thread_id}/read", status_code=204)
def mark_student_chat_thread_read(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    thread = db.query(StudentChatThread).filter(StudentChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    student = _resolve_student(db, current_user)
    if not _user_can_access_thread(db, thread, current_user, student):
        raise HTTPException(status_code=403, detail="Access denied")
    _mark_staff_incoming_read(db, thread, current_user.id)
    db.commit()
    return Response(status_code=204)


@router.get("/messages/threads/{thread_id}/messages")
def list_student_chat_messages(
    thread_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    thread = db.query(StudentChatThread).filter(StudentChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    student = _resolve_student(db, current_user)
    if not _user_can_access_thread(db, thread, current_user, student):
        raise HTTPException(status_code=403, detail="Access denied")
    _mark_staff_incoming_delivered(db, thread, current_user.id)
    db.commit()
    msgs = (
        db.query(StudentChatMessage)
        .filter(StudentChatMessage.thread_id == thread_id, StudentChatMessage.deleted_at.is_(None))
        .order_by(StudentChatMessage.created_at.asc(), StudentChatMessage.id.asc())
        .limit(500)
        .all()
    )
    user_ids = {m.sender_user_id for m in msgs}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    items = []
    for m in msgs:
        u = users.get(m.sender_user_id)
        label = f"{(u.firstname or '').strip()} {(u.lastname or '').strip()}".strip() if u else f"User #{m.sender_user_id}"
        items.append(
            {
                "id": m.id,
                "parent_message_id": m.parent_message_id,
                "sender_user_id": m.sender_user_id,
                "sender_label": label,
                "body": m.body,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "delivered_at": m.delivered_at.isoformat() if getattr(m, "delivered_at", None) else None,
                "read_at": m.read_at.isoformat() if getattr(m, "read_at", None) else None,
            }
        )
    return {"thread_id": thread_id, "items": items}


@router.post("/messages/threads/{thread_id}/messages", status_code=201)
def post_student_chat_message(
    thread_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    thread = db.query(StudentChatThread).filter(StudentChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    student = _resolve_student(db, current_user)
    if not _user_can_access_thread(db, thread, current_user, student):
        raise HTTPException(status_code=403, detail="Access denied")
    if payload.parent_message_id:
        parent = (
            db.query(StudentChatMessage)
            .filter(
                StudentChatMessage.id == payload.parent_message_id,
                StudentChatMessage.thread_id == thread_id,
                StudentChatMessage.deleted_at.is_(None),
            )
            .first()
        )
        if not parent:
            raise HTTPException(status_code=400, detail="Invalid parent_message_id")
    msg = StudentChatMessage(
        thread_id=thread_id,
        parent_message_id=payload.parent_message_id,
        sender_user_id=current_user.id,
        body=payload.body.strip(),
    )
    db.add(msg)
    thread.updated_at = datetime.utcnow()
    db.add(thread)
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "delivered_at": msg.delivered_at.isoformat() if getattr(msg, "delivered_at", None) else None,
        "read_at": msg.read_at.isoformat() if getattr(msg, "read_at", None) else None,
    }
