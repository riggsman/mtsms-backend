from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.grading_method import GradingMethod, GradingRange
from app.models.student_record import StudentRecord

Number = Union[int, float, Decimal]


DEFAULT_GRADING_RANGES: List[Dict[str, Any]] = [
    {"minimum_score": 0.0, "maximum_score": 59.99, "grade": "F", "grade_point": 0.0},
    {"minimum_score": 60.0, "maximum_score": 69.99, "grade": "D", "grade_point": 1.0},
    {"minimum_score": 70.0, "maximum_score": 79.99, "grade": "C", "grade_point": 2.0},
    {"minimum_score": 80.0, "maximum_score": 89.99, "grade": "B", "grade_point": 3.0},
    {"minimum_score": 90.0, "maximum_score": 100.0, "grade": "A", "grade_point": 4.0},
]


class GPAEngine:
    @staticmethod
    def calculate_grade(
        score: Number,
        course_weight: Number,
        grading_ranges: Sequence[GradingRange],
    ) -> Dict[str, Any]:
        numeric_score = float(score)
        weight = float(course_weight or 1.0)

        for grading in grading_ranges:
            if grading.minimum_score <= numeric_score <= grading.maximum_score:
                weighted_points = float(grading.grade_point) * weight
                return {
                    "score": numeric_score,
                    "grade": grading.grade,
                    "grade_point": float(grading.grade_point),
                    "course_weight": weight,
                    "weighted_points": weighted_points,
                }

        return {
            "score": numeric_score,
            "grade": "N/A",
            "grade_point": 0.0,
            "course_weight": weight,
            "weighted_points": 0.0,
        }


def get_grading_method(db: Session, institution_id: Optional[int]) -> Optional[GradingMethod]:
    """Return tenant grading method, or the platform default when none is configured."""
    grading_method = None
    if institution_id is not None:
        grading_method = (
            db.query(GradingMethod)
            .filter(GradingMethod.institution_id == institution_id)
            .first()
        )

    if grading_method is None:
        grading_method = (
            db.query(GradingMethod)
            .filter(GradingMethod.is_system_default.is_(True))
            .first()
        )

    return grading_method


def get_grading_ranges(db: Session, institution_id: Optional[int]) -> List[GradingRange]:
    grading_method = get_grading_method(db, institution_id)
    if grading_method and grading_method.grading_ranges:
        return list(grading_method.grading_ranges)
    return []


def resolve_course_weight(
    db: Session,
    institution_id: int,
    course_code: str,
) -> Decimal:
    course = (
        db.query(Course)
        .filter(
            Course.institution_id == institution_id,
            Course.code == course_code,
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if course and course.credits is not None:
        return Decimal(str(course.credits))
    return Decimal("1.0")


def calculate_record_grading(
    db: Session,
    institution_id: int,
    total_score: Number,
    course_code: str,
    course_weight: Optional[Number] = None,
) -> Tuple[str, Decimal, Decimal, Decimal]:
    """
    Resolve letter grade and per-course grade point using tenant grading ranges.

    Returns:
        letter_grade, grade_point (stored in student_records.gpa),
        course_weight, weighted_points
    """
    weight = (
        Decimal(str(course_weight))
        if course_weight is not None
        else resolve_course_weight(db, institution_id, course_code)
    )
    grading_ranges = get_grading_ranges(db, institution_id)
    result = GPAEngine.calculate_grade(total_score, weight, grading_ranges)

    return (
        result["grade"],
        Decimal(str(result["grade_point"])).quantize(Decimal("0.01")),
        Decimal(str(result["course_weight"])).quantize(Decimal("0.1")),
        Decimal(str(result["weighted_points"])).quantize(Decimal("0.01")),
    )


def calculate_cumulative_gpa(records: Iterable[StudentRecord]) -> float:
    """
    Credit-weighted cumulative GPA:
    sum(grade_point * course_weight) / sum(course_weight)
    """
    total_weight = 0.0
    total_points = 0.0

    for record in records:
        weight = float(record.course_weight or 1.0)
        grade_point = float(record.gpa or 0.0)
        total_weight += weight
        total_points += grade_point * weight

    if total_weight <= 0:
        return 0.0
    return round(total_points / total_weight, 2)


def get_grade_point_from_letter(
    db: Session,
    institution_id: Optional[int],
    letter_grade: Optional[str],
) -> float:
    if not letter_grade:
        return 0.0

    normalized = letter_grade.strip().upper()
    for grading in get_grading_ranges(db, institution_id):
        if grading.grade.upper() == normalized:
            return float(grading.grade_point)

    for default in DEFAULT_GRADING_RANGES:
        if default["grade"] == normalized:
            return float(default["grade_point"])
    return 0.0


def ensure_system_default_grading_method(db: Session) -> GradingMethod:
    existing = (
        db.query(GradingMethod)
        .filter(GradingMethod.is_system_default.is_(True))
        .first()
    )
    if existing:
        return existing

    grading_method = GradingMethod(
        name="System Default (4.0 Scale)",
        institution_id=None,
        is_system_default=True,
    )
    db.add(grading_method)
    db.flush()

    for row in DEFAULT_GRADING_RANGES:
        db.add(
            GradingRange(
                grading_method_id=grading_method.id,
                minimum_score=row["minimum_score"],
                maximum_score=row["maximum_score"],
                grade=row["grade"],
                grade_point=row["grade_point"],
            )
        )

    db.commit()
    db.refresh(grading_method)
    return grading_method
