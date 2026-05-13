import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.classes import Class
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.student_promotion_history import StudentPromotionHistory
from app.models.student_year_outcome import StudentYearOutcome


def _extract_level_number(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _guess_class_level(cls: Class) -> Optional[int]:
    for candidate in (getattr(cls, "code", None), getattr(cls, "name", None)):
        level = _extract_level_number(candidate)
        if level is not None:
            return level
    return None


def _build_target_class_map(classes: Sequence[Class]) -> Dict[int, int]:
    grouped: Dict[str, List[Tuple[int, Class]]] = {}
    for cls in classes:
        level = _guess_class_level(cls)
        if level is None:
            continue
        group_key = f"{(cls.institution_level or '').lower()}::{(cls.category or '').lower()}"
        grouped.setdefault(group_key, []).append((level, cls))

    target_map: Dict[int, int] = {}
    for entries in grouped.values():
        entries_sorted = sorted(entries, key=lambda x: (x[0], x[1].id))
        for idx, (_, current_cls) in enumerate(entries_sorted):
            if idx + 1 < len(entries_sorted):
                target_map[current_cls.id] = entries_sorted[idx + 1][1].id
    return target_map


def build_promotion_preview(
    db: Session,
    institution_id: int,
    academic_year_id: int,
    final_status: str = "promoted",
    student_ids: Optional[Sequence[int]] = None,
) -> List[dict]:
    outcomes_q = db.query(StudentYearOutcome).filter(
        StudentYearOutcome.institution_id == institution_id,
        StudentYearOutcome.academic_year_id == academic_year_id,
        StudentYearOutcome.final_status == final_status,
        StudentYearOutcome.deleted_at.is_(None),
    )
    if student_ids:
        outcomes_q = outcomes_q.filter(StudentYearOutcome.student_id.in_(list(student_ids)))
    outcomes = outcomes_q.all()
    if not outcomes:
        return []

    outcome_ids = sorted({o.student_id for o in outcomes})
    students = (
        db.query(Student)
        .filter(
            Student.institution_id == institution_id,
            Student.id.in_(outcome_ids),
            Student.deleted_at.is_(None),
        )
        .all()
    )
    students_by_id = {s.id: s for s in students}

    class_ids = sorted({s.class_id for s in students if s.class_id is not None})
    classes = (
        db.query(Class)
        .filter(
            Class.institution_id == institution_id,
            Class.id.in_(class_ids),
            Class.deleted_at.is_(None),
        )
        .all()
    )
    class_by_id = {c.id: c for c in classes}
    target_map = _build_target_class_map(classes)

    items: List[dict] = []
    for outcome in outcomes:
        student = students_by_id.get(outcome.student_id)
        if not student:
            items.append(
                {
                    "student_id": outcome.student_id,
                    "student_name": f"Student #{outcome.student_id}",
                    "from_class_id": 0,
                    "from_class_name": None,
                    "to_class_id": None,
                    "to_class_name": None,
                    "reason": "student_not_found",
                }
            )
            continue

        from_class = class_by_id.get(student.class_id)
        to_class_id = target_map.get(student.class_id)
        to_class = class_by_id.get(to_class_id) if to_class_id is not None else None
        reason = None if to_class_id else "next_class_not_resolved"

        items.append(
            {
                "student_id": student.id,
                "student_name": " ".join(filter(None, [student.firstname, student.lastname])) or f"Student #{student.id}",
                "from_class_id": int(student.class_id or 0),
                "from_class_name": from_class.name if from_class else None,
                "to_class_id": to_class.id if to_class else None,
                "to_class_name": to_class.name if to_class else None,
                "reason": reason,
            }
        )
    return items


def execute_promotion(
    db: Session,
    institution_id: int,
    academic_year_id: int,
    actor_user_id: Optional[int],
    final_status: str = "promoted",
    student_ids: Optional[Sequence[int]] = None,
) -> dict:
    preview = build_promotion_preview(
        db=db,
        institution_id=institution_id,
        academic_year_id=academic_year_id,
        final_status=final_status,
        student_ids=student_ids,
    )
    execution_id = uuid.uuid4().hex

    moved = 0
    archived = 0
    skipped = 0
    errors: List[str] = []

    if not preview:
        return {"execution_id": execution_id, "moved": 0, "archived": 0, "skipped": 0, "errors": []}

    students = (
        db.query(Student)
        .filter(
            Student.institution_id == institution_id,
            Student.id.in_([p["student_id"] for p in preview]),
            Student.deleted_at.is_(None),
        )
        .all()
    )
    student_by_id = {s.id: s for s in students}

    for item in preview:
        sid = item["student_id"]
        student = student_by_id.get(sid)
        if not student:
            skipped += 1
            errors.append(f"student_not_found:{sid}")
            continue

        if not item.get("to_class_id"):
            skipped += 1
            continue

        try:
            enrollment_rows = (
                db.query(Enrollment)
                .filter(
                    Enrollment.institution_id == institution_id,
                    Enrollment.student_id == sid,
                    Enrollment.deleted_at.is_(None),
                )
                .all()
            )

            student_snapshot = {
                "id": student.id,
                "firstname": student.firstname,
                "lastname": student.lastname,
                "student_id": student.student_id,
                "from_class_id": student.class_id,
                "academic_year_id": student.academic_year_id,
                "level": student.level,
            }
            enrollment_snapshot = [
                {
                    "id": e.id,
                    "course_id": e.course_id,
                    "status": e.status,
                    "enrollment_date": e.enrollment_date.isoformat() if e.enrollment_date else None,
                }
                for e in enrollment_rows
            ]

            history = StudentPromotionHistory(
                institution_id=institution_id,
                student_id=sid,
                academic_year_id=academic_year_id,
                from_class_id=item["from_class_id"],
                to_class_id=item["to_class_id"],
                final_status=final_status,
                archived_student_snapshot=json.dumps(student_snapshot),
                archived_enrollment_snapshot=json.dumps(enrollment_snapshot),
                promoted_by=actor_user_id,
                promoted_at=datetime.utcnow(),
                execution_id=execution_id,
            )
            db.add(history)
            archived += 1

            student.class_id = item["to_class_id"]
            student.academic_year_id = academic_year_id
            moved += 1
        except Exception as exc:
            skipped += 1
            errors.append(f"{sid}:{exc}")

    db.commit()
    return {
        "execution_id": execution_id,
        "moved": moved,
        "archived": archived,
        "skipped": skipped,
        "errors": errors,
    }
