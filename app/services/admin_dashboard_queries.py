"""Tenant admin dashboard aggregates (stats, trends, recent reports)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.helpers.user_roles import role_column_exclude_pure_role
from app.models.activity import Activity
from app.models.course import Course
from app.models.student import Student
from app.models.user import User


def _trend_percent(recent: int, prior: int) -> dict[str, Any]:
    if prior == 0:
        if recent == 0:
            return {"direction": "stable", "label": "0%", "change": 0.0}
        return {"direction": "up", "label": "+100%", "change": 100.0}
    change = ((recent - prior) / prior) * 100
    if change > 0:
        direction = "up"
        label = f"+{round(change)}%"
    elif change < 0:
        direction = "down"
        label = f"{round(change)}%"
    else:
        direction = "stable"
        label = "0%"
    return {"direction": direction, "label": label, "change": round(change, 1)}


def _trend_absolute(recent: int, prior: int) -> dict[str, Any]:
    diff = recent - prior
    if diff > 0:
        direction, label = "up", f"+{diff}"
    elif diff < 0:
        direction, label = "down", str(diff)
    else:
        direction, label = "stable", "0"
    return {"direction": direction, "label": label, "change": diff}


def _count_created_between(
    db: Session,
    model,
    institution_id: Optional[int],
    start: datetime,
    end: datetime,
    *,
    extra_filter=None,
) -> int:
    q = db.query(func.count(model.id)).filter(
        model.deleted_at.is_(None),
        model.created_at >= start,
        model.created_at < end,
    )
    if institution_id is not None and hasattr(model, "institution_id"):
        q = q.filter(model.institution_id == institution_id)
    if extra_filter is not None:
        q = extra_filter(q)
    return int(q.scalar() or 0)


def _total_count(db: Session, model, institution_id: Optional[int], *, extra_filter=None) -> int:
    q = db.query(func.count(model.id)).filter(model.deleted_at.is_(None))
    if institution_id is not None and hasattr(model, "institution_id"):
        q = q.filter(model.institution_id == institution_id)
    if extra_filter is not None:
        q = extra_filter(q)
    return int(q.scalar() or 0)


def _staff_filter(bind):
    return lambda q: q.filter(role_column_exclude_pure_role(bind, User.role, "student"))


def _infer_report_format(title: str, content: Optional[str]) -> str:
    text = f"{title} {content or ''}".lower()
    if ".xlsx" in text or "excel" in text:
        return "excel"
    if ".csv" in text or "csv" in text:
        return "csv"
    return "pdf"


def _format_icon(report_format: str) -> str:
    if report_format == "excel":
        return "fa-file-excel"
    if report_format == "csv":
        return "fa-file-csv"
    return "fa-file-pdf"


def get_admin_dashboard_overview(db: Session, institution_id: Optional[int]) -> dict[str, Any]:
    """Stats, period trends (last 30d vs prior 30d), and recent report-like activities."""
    now = datetime.utcnow()
    recent_start = now - timedelta(days=30)
    prior_start = now - timedelta(days=60)
    prior_end = recent_start

    bind = db.get_bind()
    staff_extra = _staff_filter(bind)

    total_students = _total_count(db, Student, institution_id)
    total_staff = _total_count(db, User, institution_id, extra_filter=staff_extra)
    active_courses = _total_count(db, Course, institution_id)

    recent_students = _count_created_between(db, Student, institution_id, recent_start, now)
    prior_students = _count_created_between(db, Student, institution_id, prior_start, prior_end)
    recent_staff = _count_created_between(
        db, User, institution_id, recent_start, now, extra_filter=staff_extra
    )
    prior_staff = _count_created_between(
        db, User, institution_id, prior_start, prior_end, extra_filter=staff_extra
    )
    recent_courses = _count_created_between(db, Course, institution_id, recent_start, now)
    prior_courses = _count_created_between(db, Course, institution_id, prior_start, prior_end)

    trends = {
        "students": _trend_percent(recent_students, prior_students),
        "staff": _trend_absolute(recent_staff, prior_staff),
        "courses": _trend_absolute(recent_courses, prior_courses),
    }

    recent_reports: list[dict[str, Any]] = []
    if institution_id is not None:
        report_activities = (
            db.query(Activity)
            .filter(
                Activity.institution_id == institution_id,
                or_(
                    Activity.action.ilike("%report%"),
                    Activity.action.ilike("%export%"),
                    Activity.content.ilike("%report%"),
                    Activity.content.ilike("%export%"),
                ),
            )
            .order_by(Activity.created_at.desc())
            .limit(10)
            .all()
        )
        for act in report_activities:
            title = (act.action or "Report").strip()
            if act.content and len(act.content) < 120:
                title = act.content.strip()
            report_format = _infer_report_format(title, act.content)
            recent_reports.append(
                {
                    "id": act.id,
                    "title": title,
                    "format": report_format,
                    "icon": _format_icon(report_format),
                    "generatedAt": act.created_at.isoformat() if act.created_at else None,
                    "downloadUrl": None,
                }
            )

    return {
        "stats": {
            "totalStudents": total_students,
            "totalStaff": total_staff,
            "activeCourses": active_courses,
            "newAdmissions": recent_students,
        },
        "trends": trends,
        "recentReports": recent_reports,
    }
