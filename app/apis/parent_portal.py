"""Read-only data for parent portal (linked students by guardian email)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.classes import Class
from app.models.guardian import Guardian
from app.models.student import Student
from app.models.student_attendance_entry import StudentAttendanceEntry
from app.models.student_record import StudentRecord
from app.models.user import User


def list_children_for_parent_user(db: Session, current_user: User) -> List[Student]:
    if not current_user or not current_user.institution_id:
        return []
    email = (current_user.email or "").strip().lower()
    if not email:
        return []

    q = (
        db.query(Student)
        .join(Guardian, Guardian.id == Student.guardian_id)
        .filter(
            Student.institution_id == current_user.institution_id,
            Student.deleted_at.is_(None),
            Guardian.deleted_at.is_(None),
            Guardian.email.isnot(None),
            func.lower(func.trim(Guardian.email)) == email,
        )
        .order_by(Student.lastname.asc(), Student.firstname.asc())
    )
    return q.all()


def get_child_for_parent(db: Session, current_user: User, student_pk: int) -> Optional[Student]:
    for row in list_children_for_parent_user(db, current_user):
        if row.id == student_pk:
            return row
    return None


def _class_label(db: Session, institution_id: int, class_id: int) -> Optional[str]:
    c = (
        db.query(Class)
        .filter(
            Class.id == class_id,
            Class.institution_id == institution_id,
            Class.deleted_at.is_(None),
        )
        .first()
    )
    return c.name if c else None


def child_summary(db: Session, student: Student) -> Dict[str, Any]:
    """Aggregate grades + attendance + recent announcements for one child."""
    inst_id = student.institution_id
    sid = student.student_id

    records = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.institution_id == inst_id,
            StudentRecord.student_id == sid,
            StudentRecord.deleted_at.is_(None),
        )
        .order_by(StudentRecord.id.desc())
        .limit(50)
        .all()
    )

    grades_out: List[Dict[str, Any]] = []
    for r in records:
        grades_out.append(
            {
                "course_code": r.course_code,
                "semester": r.semester,
                "academic_year": r.academic_year,
                "assignment": float(r.assignment or 0),
                "ca": float(r.ca or 0),
                "exam": float(r.exam or 0),
                "total_score": float(r.total_score) if r.total_score is not None else None,
                "letter_grade": r.letter_grade,
                "gpa": float(r.gpa) if r.gpa is not None else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
        )

    since = datetime.utcnow().date() - timedelta(days=120)
    att_rows = (
        db.query(StudentAttendanceEntry)
        .filter(
            StudentAttendanceEntry.institution_id == inst_id,
            StudentAttendanceEntry.student_id == sid,
            StudentAttendanceEntry.deleted_at.is_(None),
            StudentAttendanceEntry.session_date >= since,
        )
        .all()
    )
    total_sessions = len(att_rows)
    present = sum(1 for a in att_rows if (a.status or "").lower() in ("present", "late", "excused"))
    absent = sum(1 for a in att_rows if (a.status or "").lower() == "absent")

    ann = (
        db.query(Announcement)
        .filter(
            Announcement.institution_id == inst_id,
            Announcement.deleted_at.is_(None),
        )
        .order_by(Announcement.created_at.desc())
        .limit(8)
        .all()
    )
    notifications: List[Dict[str, Any]] = []
    for a in ann:
        aud = (a.target_audience or "all").lower()
        if aud not in ("all", "students"):
            continue
        notifications.append(
            {
                "id": a.id,
                "title": a.title,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "target_audience": a.target_audience,
            }
        )

    return {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "firstname": student.firstname,
            "lastname": student.lastname,
            "level": student.level,
            "class_name": _class_label(db, inst_id, student.class_id),
        },
        "grades": grades_out,
        "attendance": {
            "window_days": 120,
            "total_sessions": total_sessions,
            "present_or_equivalent": present,
            "absent": absent,
            "rate": round((present / total_sessions) * 100, 1) if total_sessions else None,
        },
        "notifications": notifications,
        "reports": {
            "message": "Official transcripts and PDF reports can be requested from the school office.",
        },
    }
