from typing import List, Optional

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.grading_method import GradingMethod, GradingRange
from app.services.gpa_service import ensure_system_default_grading_method, get_grading_method


def _validate_ranges(ranges: List[dict]) -> None:
    if not ranges:
        raise ValidationError("At least one grading range is required")

    sorted_ranges = sorted(ranges, key=lambda row: row["minimum_score"])
    for row in sorted_ranges:
        if row["minimum_score"] > row["maximum_score"]:
            raise ValidationError(
                f"Invalid range for grade {row['grade']}: minimum_score cannot exceed maximum_score"
            )

    for idx in range(1, len(sorted_ranges)):
        previous = sorted_ranges[idx - 1]
        current = sorted_ranges[idx]
        if current["minimum_score"] <= previous["maximum_score"]:
            raise ValidationError("Grading ranges must not overlap")


def get_effective_grading_method(
    db: Session,
    institution_id: Optional[int],
) -> GradingMethod:
    ensure_system_default_grading_method(db)
    grading_method = get_grading_method(db, institution_id)
    if grading_method is None:
        raise NotFoundError("No grading method configured")
    return grading_method


def get_system_default_grading_method(db: Session) -> GradingMethod:
    ensure_system_default_grading_method(db)
    grading_method = (
        db.query(GradingMethod)
        .filter(GradingMethod.is_system_default.is_(True))
        .first()
    )
    if grading_method is None:
        raise NotFoundError("System default grading method is not configured")
    return grading_method


def upsert_system_default_grading_method(
    db: Session,
    name: str,
    ranges: List[dict],
) -> GradingMethod:
    _validate_ranges(ranges)
    ensure_system_default_grading_method(db)

    grading_method = (
        db.query(GradingMethod)
        .filter(GradingMethod.is_system_default.is_(True))
        .first()
    )
    if grading_method is None:
        raise NotFoundError("System default grading method is not configured")

    grading_method.name = name
    db.query(GradingRange).filter(
        GradingRange.grading_method_id == grading_method.id
    ).delete(synchronize_session=False)

    for row in sorted(ranges, key=lambda item: item["minimum_score"]):
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


def upsert_tenant_grading_method(
    db: Session,
    institution_id: int,
    name: str,
    ranges: List[dict],
) -> GradingMethod:
    _validate_ranges(ranges)

    grading_method = (
        db.query(GradingMethod)
        .filter(GradingMethod.institution_id == institution_id)
        .first()
    )

    if grading_method is None:
        grading_method = GradingMethod(
            name=name,
            institution_id=institution_id,
            is_system_default=False,
        )
        db.add(grading_method)
        db.flush()
    else:
        grading_method.name = name
        db.query(GradingRange).filter(
            GradingRange.grading_method_id == grading_method.id
        ).delete(synchronize_session=False)

    for row in sorted(ranges, key=lambda item: item["minimum_score"]):
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
