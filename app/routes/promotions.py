from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.dependencies.tenantDependency import get_db
from app.models.academic_year import AcademicYear
from app.models.role import UserRole
from app.models.student_year_outcome import StudentYearOutcome
from app.models.user import User
from app.schemas.promotion import (
    PromotionExecuteRequest,
    PromotionExecuteResponse,
    PromotionPreviewRequest,
    PromotionPreviewResponse,
    StudentYearOutcomeResponse,
    StudentYearOutcomeUpsertRequest,
)
from app.services.promotion_service import build_promotion_preview, execute_promotion


promotions_router = APIRouter()


def _require_institution_id(user: User) -> int:
    if not user.institution_id:
        raise HTTPException(status_code=400, detail="institution_id missing for current user")
    return int(user.institution_id)


@promotions_router.post(
    "/promotions/outcomes",
    response_model=StudentYearOutcomeResponse,
)
def upsert_student_year_outcome(
    body: StudentYearOutcomeUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)),
):
    institution_id = _require_institution_id(current_user)
    year = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.id == body.academic_year_id,
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found")

    status_value = body.final_status.strip().lower()
    allowed = {"promoted", "repeated", "graduated", "transferred"}
    if status_value not in allowed:
        raise HTTPException(status_code=400, detail=f"final_status must be one of {sorted(allowed)}")

    row = (
        db.query(StudentYearOutcome)
        .filter(
            StudentYearOutcome.institution_id == institution_id,
            StudentYearOutcome.student_id == body.student_id,
            StudentYearOutcome.academic_year_id == body.academic_year_id,
            StudentYearOutcome.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        row = StudentYearOutcome(
            institution_id=institution_id,
            student_id=body.student_id,
            academic_year_id=body.academic_year_id,
            term=body.term,
            final_status=status_value,
            notes=body.notes,
            decided_by=current_user.id,
        )
        db.add(row)
    else:
        row.term = body.term
        row.final_status = status_value
        row.notes = body.notes
        row.decided_by = current_user.id
    db.commit()
    db.refresh(row)
    return row


@promotions_router.get("/promotions/candidates", response_model=PromotionPreviewResponse)
def get_promotion_candidates(
    academic_year_id: int,
    final_status: str = "promoted",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    institution_id = _require_institution_id(current_user)
    items = build_promotion_preview(
        db=db,
        institution_id=institution_id,
        academic_year_id=academic_year_id,
        final_status=final_status.strip().lower(),
    )
    mapped = sum(1 for i in items if i.get("to_class_id"))
    unresolved = len(items) - mapped
    return {
        "eligible_count": len(items),
        "mapped_count": mapped,
        "unresolved_count": unresolved,
        "items": items,
    }


@promotions_router.post("/promotions/preview", response_model=PromotionPreviewResponse)
def preview_promotions(
    body: PromotionPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    institution_id = _require_institution_id(current_user)
    items = build_promotion_preview(
        db=db,
        institution_id=institution_id,
        academic_year_id=body.academic_year_id,
        final_status=body.final_status.strip().lower(),
        student_ids=body.student_ids,
    )
    mapped = sum(1 for i in items if i.get("to_class_id"))
    unresolved = len(items) - mapped
    return {
        "eligible_count": len(items),
        "mapped_count": mapped,
        "unresolved_count": unresolved,
        "items": items,
    }


@promotions_router.post("/promotions/execute", response_model=PromotionExecuteResponse)
def execute_promotions(
    body: PromotionExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY)),
):
    institution_id = _require_institution_id(current_user)
    payload = execute_promotion(
        db=db,
        institution_id=institution_id,
        academic_year_id=body.academic_year_id,
        actor_user_id=current_user.id,
        final_status=body.final_status.strip().lower(),
        student_ids=body.student_ids,
    )
    return payload
