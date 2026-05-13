import datetime
from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.classes import Class
from app.models.student import Student
from app.models.student_course_rank import StudentCourseRank
from app.models.student_record import StudentRecord


def _safe_score(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def compute_dense_rank(sorted_pairs: Sequence[Tuple[str, Decimal]]) -> List[Tuple[str, Decimal, int]]:
    ranked: List[Tuple[str, Decimal, int]] = []
    current_rank = 0
    previous_score: Optional[Decimal] = None
    for student_id, score in sorted_pairs:
        normalized = _safe_score(score)
        if previous_score is None or normalized != previous_score:
            current_rank += 1
            previous_score = normalized
        ranked.append((str(student_id), normalized, current_rank))
    return ranked


def rank_students_per_course(
    db: Session,
    institution_id: int,
    course_code: str,
    semester_or_term: str,
    academic_year: str,
) -> Dict[str, Any]:
    rows = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.institution_id == institution_id,
            StudentRecord.course_code == course_code,
            StudentRecord.semester == semester_or_term,
            StudentRecord.deleted_at.is_(None),
        )
        .all()
    )
    ordered = sorted(
        [(str(r.student_id), _safe_score(r.total_score), r.updated_at) for r in rows],
        key=lambda item: (-item[1], item[0]),
    )
    ranked_rows = compute_dense_rank([(sid, score) for sid, score, _ in ordered])
    now = datetime.datetime.utcnow()

    existing = (
        db.query(StudentCourseRank)
        .filter(
            StudentCourseRank.institution_id == institution_id,
            StudentCourseRank.course_code == course_code,
            StudentCourseRank.academic_year == academic_year,
            StudentCourseRank.semester_or_term == semester_or_term,
            StudentCourseRank.deleted_at.is_(None),
        )
        .all()
    )
    existing_map = {str(item.student_id): item for item in existing}
    present_student_ids = set()

    for student_id, score, dense_rank in ranked_rows:
        present_student_ids.add(student_id)
        source_updated_at = None
        for sid, _, updated_at in ordered:
            if sid == student_id:
                source_updated_at = updated_at
                break
        row = existing_map.get(student_id)
        if row:
            row.score = score
            row.dense_rank = dense_rank
            row.computed_at = now
            row.source_updated_at = source_updated_at
            row.deleted_at = None
            row.updated_at = now
        else:
            db.add(
                StudentCourseRank(
                    institution_id=institution_id,
                    student_id=student_id,
                    course_code=course_code,
                    academic_year=academic_year,
                    semester_or_term=semester_or_term,
                    score=score,
                    dense_rank=dense_rank,
                    computed_at=now,
                    source_updated_at=source_updated_at,
                    created_at=now,
                )
            )

    for student_id, row in existing_map.items():
        if student_id not in present_student_ids:
            row.deleted_at = now
            row.updated_at = now

    db.commit()
    return {
        "institution_id": institution_id,
        "course_code": course_code,
        "academic_year": academic_year,
        "semester_or_term": semester_or_term,
        "rows_upserted": len(ranked_rows),
        "computed_at": now.isoformat(),
    }


def rank_students_overall(db: Session, institution_id: int, top_n: int = 3) -> List[Dict[str, Any]]:
    rows = (
        db.query(
            StudentRecord.student_id.label("student_id"),
            func.sum(StudentRecord.total_score).label("total_score"),
            Student.firstname,
            Student.lastname,
            Student.class_id,
            Student.school_id,
        )
        .join(
            Student,
            (Student.institution_id == StudentRecord.institution_id)
            & (Student.student_id == StudentRecord.student_id)
            & Student.deleted_at.is_(None),
        )
        .filter(
            StudentRecord.institution_id == institution_id,
            StudentRecord.deleted_at.is_(None),
        )
        .group_by(
            StudentRecord.student_id,
            Student.firstname,
            Student.lastname,
            Student.class_id,
            Student.school_id,
        )
        .all()
    )
    ordered = sorted(rows, key=lambda item: (-_safe_score(item.total_score), str(item.student_id)))
    ranked = compute_dense_rank([(str(item.student_id), _safe_score(item.total_score)) for item in ordered])
    rank_lookup = {sid: rank for sid, _, rank in ranked}
    return [
        {
            "student_id": str(item.student_id),
            "name": f"{item.firstname or ''} {item.lastname or ''}".strip() or str(item.student_id),
            "score": float(_safe_score(item.total_score)),
            "rank": rank_lookup.get(str(item.student_id), 0),
            "class_id": item.class_id,
            "school_id": item.school_id,
        }
        for item in ordered[:top_n]
    ]


def rank_classes(db: Session, institution_id: int, top_n: int = 3) -> List[Dict[str, Any]]:
    rows = (
        db.query(
            Student.class_id.label("class_id"),
            func.avg(StudentRecord.total_score).label("avg_score"),
            Class.name.label("class_name"),
        )
        .join(
            Student,
            (Student.institution_id == StudentRecord.institution_id)
            & (Student.student_id == StudentRecord.student_id)
            & Student.deleted_at.is_(None),
        )
        .outerjoin(
            Class,
            (Class.id == Student.class_id)
            & (Class.institution_id == Student.institution_id)
            & Class.deleted_at.is_(None),
        )
        .filter(
            StudentRecord.institution_id == institution_id,
            StudentRecord.deleted_at.is_(None),
        )
        .group_by(Student.class_id, Class.name)
        .all()
    )
    ordered = sorted(rows, key=lambda item: (-_safe_score(item.avg_score), int(item.class_id or 0)))
    ranked = compute_dense_rank([(str(item.class_id), _safe_score(item.avg_score)) for item in ordered])
    rank_lookup = {cid: rank for cid, _, rank in ranked}
    return [
        {
            "class_id": item.class_id,
            "name": item.class_name or f"Class {item.class_id}",
            "score": float(_safe_score(item.avg_score)),
            "rank": rank_lookup.get(str(item.class_id), 0),
        }
        for item in ordered[:top_n]
    ]


def rank_schools(db: Session, institution_id: int, top_n: int = 3) -> List[Dict[str, Any]]:
    rows = (
        db.query(
            Student.school_id.label("school_id"),
            func.avg(StudentRecord.total_score).label("avg_score"),
        )
        .join(
            Student,
            (Student.institution_id == StudentRecord.institution_id)
            & (Student.student_id == StudentRecord.student_id)
            & Student.deleted_at.is_(None),
        )
        .filter(
            StudentRecord.institution_id == institution_id,
            StudentRecord.deleted_at.is_(None),
        )
        .group_by(Student.school_id)
        .all()
    )
    ordered = sorted(rows, key=lambda item: (-_safe_score(item.avg_score), int(item.school_id or 0)))
    ranked = compute_dense_rank([(str(item.school_id), _safe_score(item.avg_score)) for item in ordered])
    rank_lookup = {sid: rank for sid, _, rank in ranked}
    return [
        {
            "school_id": item.school_id,
            "name": f"School {item.school_id}",
            "score": float(_safe_score(item.avg_score)),
            "rank": rank_lookup.get(str(item.school_id), 0),
        }
        for item in ordered[:top_n]
    ]


def get_student_course_rank_rows(
    db: Session,
    institution_id: int,
    student_id: str,
    academic_year: Optional[str] = None,
    semester_or_term: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = db.query(StudentCourseRank).filter(
        StudentCourseRank.institution_id == institution_id,
        StudentCourseRank.student_id == str(student_id),
        StudentCourseRank.deleted_at.is_(None),
    )
    if academic_year:
        query = query.filter(StudentCourseRank.academic_year == academic_year)
    if semester_or_term:
        query = query.filter(StudentCourseRank.semester_or_term == semester_or_term)
    rows = query.order_by(StudentCourseRank.course_code.asc()).all()
    return [
        {
            "course_code": row.course_code,
            "score": float(_safe_score(row.score)),
            "rank": row.dense_rank,
            "academic_year": row.academic_year,
            "semester_or_term": row.semester_or_term,
            "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        }
        for row in rows
    ]


def get_course_rank_rows(
    db: Session,
    institution_id: int,
    course_code: str,
    academic_year: Optional[str] = None,
    semester_or_term: Optional[str] = None,
    top_n: Optional[int] = None,
) -> List[Dict[str, Any]]:
    query = db.query(StudentCourseRank).filter(
        StudentCourseRank.institution_id == institution_id,
        StudentCourseRank.course_code == course_code,
        StudentCourseRank.deleted_at.is_(None),
    )
    if academic_year:
        query = query.filter(StudentCourseRank.academic_year == academic_year)
    if semester_or_term:
        query = query.filter(StudentCourseRank.semester_or_term == semester_or_term)
    query = query.order_by(StudentCourseRank.dense_rank.asc(), StudentCourseRank.student_id.asc())
    if top_n and top_n > 0:
        query = query.limit(top_n)
    rows = query.all()
    return [
        {
            "student_id": str(row.student_id),
            "course_code": row.course_code,
            "score": float(_safe_score(row.score)),
            "dense_rank": row.dense_rank,
            "academic_year": row.academic_year,
            "semester_or_term": row.semester_or_term,
            "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        }
        for row in rows
    ]


def summarize_latest_academic_year_by_semester(
    db: Session, institution_id: int, semester_or_term: str
) -> Optional[str]:
    rows = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.institution_id == institution_id,
            StudentRecord.semester == semester_or_term,
            StudentRecord.deleted_at.is_(None),
        )
        .order_by(StudentRecord.created_at.desc())
        .limit(1)
        .all()
    )
    if not rows:
        return None
    created = rows[0].created_at or datetime.datetime.utcnow()
    return str(created.year)


def build_overview_rankings_payload(
    db: Session,
    institution_id: int,
    top_n: int = 3,
) -> Dict[str, Any]:
    students = rank_students_overall(db=db, institution_id=institution_id, top_n=top_n)
    classes = rank_classes(db=db, institution_id=institution_id, top_n=top_n)
    schools = rank_schools(db=db, institution_id=institution_id, top_n=top_n)
    return {"students": {"top3": students}, "classes": {"top3": classes}, "schools": {"top3": schools}}
