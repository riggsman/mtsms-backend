from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user_tenant
from app.dependencies.auth import require_any_role
from app.dependencies.tenantDependency import get_db
from app.models.announcement import Announcement
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.course import Course
from app.models.note import Note
from app.models.schedule import Schedule
from app.models.student import Student
from app.models.student_record import StudentRecord
from app.models.academic_year import AcademicYear
from app.models.tenant import Tenant
from app.models.user import User
from app.models.role import UserRole
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


def _resolve_student(db: Session, current_user: User) -> Optional[Student]:
    if not current_user or not current_user.institution_id:
        return None
    student = (
        db.query(Student)
        .filter(
            Student.institution_id == current_user.institution_id,
            Student.deleted_at.is_(None),
            Student.email == current_user.email,
        )
        .first()
    )
    return student


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
        return []
    years = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == student.institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .order_by(AcademicYear.name.asc())
        .all()
    )
    return [{"id": y.id, "name": y.name} for y in years]
