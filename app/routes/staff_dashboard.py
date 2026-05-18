"""
Staff / lecturer dashboard helpers — course attendance taking.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.apis.enrollments import get_course_enrollments
from app.apis.teachers import get_teacher_by_email, get_teacher_by_user_id
from app.dependencies.auth import require_any_role
from app.dependencies.tenantDependency import get_db
from app.helpers.user_roles import user_has_any_role
from app.models.course import Course
from app.models.role import UserRole
from app.models.student_attendance_entry import StudentAttendanceEntry
from app.models.teacher import Teacher
from app.models.user import User

router = APIRouter(prefix="/staff-dashboard", tags=["staff-dashboard"])


def _privileged_institution_staff(user: User) -> bool:
    return user_has_any_role(
        user,
        ["admin", "super_admin", "secretary"],
    )


def _resolve_teacher(db: Session, user: User) -> Optional[Teacher]:
    t = get_teacher_by_user_id(db, user.id)
    if t:
        return t
    if user.email:
        return get_teacher_by_email(db, user.email.strip())
    return None


def _course_accessible(db: Session, user: User, course: Course) -> bool:
    if not user.institution_id or course.institution_id != user.institution_id:
        return False
    if _privileged_institution_staff(user):
        return True
    teacher = _resolve_teacher(db, user)
    if not teacher or teacher.institution_id != user.institution_id:
        return False
    if course.instructor_id is None:
        return False
    return int(course.instructor_id) == int(teacher.id)


def _enrollment_in_class(status: Optional[str]) -> bool:
    s = (status or "active").lower().strip()
    if s in {"dropped", "withdrawn", "cancelled", "inactive"}:
        return False
    return True


class AttendanceSessionRowIn(BaseModel):
    student_matricule: str = Field(..., min_length=1)
    status: str = Field("present", pattern="^(present|absent|late|excused)$")
    notes: Optional[str] = Field(None, max_length=500)


class AttendanceSessionSave(BaseModel):
    course_id: int = Field(..., ge=1)
    session_date: date
    entries: List[AttendanceSessionRowIn] = Field(default_factory=list)


@router.get("/attendance/courses")
def list_courses_for_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.TEACHER,
            UserRole.SUPER_ADMIN,
            UserRole.SECRETARY,
        )
    ),
):
    """Courses the current user may record attendance for (instructor match, or admin/secretary for tenant)."""
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="Institution required")
    q = (
        db.query(Course)
        .filter(
            Course.institution_id == current_user.institution_id,
            Course.deleted_at.is_(None),
        )
        .order_by(Course.code.asc())
    )
    if _privileged_institution_staff(current_user):
        rows = q.limit(500).all()
    else:
        teacher = _resolve_teacher(db, current_user)
        if not teacher:
            return {"items": []}
        rows = (
            q.filter(Course.instructor_id == teacher.id).limit(200).all()
        )
    return {
        "items": [
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "semester": c.semester,
            }
            for c in rows
        ]
    }


@router.get("/attendance/roster")
def get_attendance_roster(
    course_id: int = Query(..., ge=1),
    session_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.TEACHER,
            UserRole.SUPER_ADMIN,
            UserRole.SECRETARY,
        )
    ),
):
    course = (
        db.query(Course)
        .filter(
            Course.id == course_id,
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not _course_accessible(db, current_user, course):
        raise HTTPException(status_code=403, detail="Not allowed for this course")

    enrollments = get_course_enrollments(
        db, course_id=course_id, institution_id=current_user.institution_id
    )
    matricules: List[str] = []
    roster: List[Dict[str, Any]] = []
    for e in enrollments:
        if not isinstance(e, dict):
            continue
        if not _enrollment_in_class(e.get("status")):
            continue
        st = e.get("student") or {}
        if not isinstance(st, dict):
            continue
        mat = st.get("student_id")
        if not mat:
            continue
        mat_s = str(mat).strip()
        if not mat_s:
            continue
        matricules.append(mat_s)
        roster.append(
            {
                "student_matricule": mat_s,
                "student_name": st.get("name"),
                "firstname": st.get("firstname"),
                "lastname": st.get("lastname"),
                "enrollment_status": e.get("status"),
            }
        )

    existing: Dict[str, StudentAttendanceEntry] = {}
    if matricules:
        rows = (
            db.query(StudentAttendanceEntry)
            .filter(
                StudentAttendanceEntry.institution_id == current_user.institution_id,
                StudentAttendanceEntry.course_code == course.code,
                StudentAttendanceEntry.session_date == session_date,
                StudentAttendanceEntry.student_id.in_(matricules),
                StudentAttendanceEntry.deleted_at.is_(None),
            )
            .all()
        )
        for r in rows:
            existing[r.student_id] = r

    items = []
    for row in roster:
        m = row["student_matricule"]
        att = existing.get(m)
        items.append(
            {
                **row,
                "attendance": (
                    None
                    if not att
                    else {
                        "id": att.id,
                        "status": att.status,
                        "notes": att.notes,
                    }
                ),
            }
        )
    return {
        "course": {"id": course.id, "code": course.code, "name": course.name},
        "session_date": session_date.isoformat(),
        "items": items,
    }


@router.post("/attendance/save-session")
def save_attendance_session(
    payload: AttendanceSessionSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(
            UserRole.ADMIN,
            UserRole.STAFF,
            UserRole.TEACHER,
            UserRole.SUPER_ADMIN,
            UserRole.SECRETARY,
        )
    ),
):
    """Upsert attendance rows for one course session."""
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="Institution required")

    course = (
        db.query(Course)
        .filter(
            Course.id == payload.course_id,
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not _course_accessible(db, current_user, course):
        raise HTTPException(status_code=403, detail="Not allowed for this course")

    enrollments = get_course_enrollments(
        db, course_id=payload.course_id, institution_id=current_user.institution_id
    )
    allowed_matricules = set()
    for e in enrollments:
        if not isinstance(e, dict):
            continue
        if not _enrollment_in_class(e.get("status")):
            continue
        st = e.get("student") or {}
        if isinstance(st, dict) and st.get("student_id"):
            allowed_matricules.add(str(st["student_id"]).strip())

    saved = 0
    for row in payload.entries:
        mat = row.student_matricule.strip()
        if mat not in allowed_matricules:
            raise HTTPException(
                status_code=400,
                detail=f"Student {mat} is not an active enrollee in this course",
            )
        q = (
            db.query(StudentAttendanceEntry)
            .filter(
                StudentAttendanceEntry.institution_id == current_user.institution_id,
                StudentAttendanceEntry.student_id == mat,
                StudentAttendanceEntry.course_code == course.code,
                StudentAttendanceEntry.session_date == payload.session_date,
                StudentAttendanceEntry.deleted_at.is_(None),
            )
        )
        existing = q.first()
        if existing:
            existing.status = row.status
            existing.notes = row.notes
            existing.recorded_by_user_id = current_user.id
        else:
            db.add(
                StudentAttendanceEntry(
                    institution_id=current_user.institution_id,
                    student_id=mat,
                    course_code=course.code,
                    session_date=payload.session_date,
                    status=row.status,
                    notes=row.notes,
                    recorded_by_user_id=current_user.id,
                )
            )
        saved += 1
    db.commit()
    return {"saved": saved, "message": "Attendance saved"}
