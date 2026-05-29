from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.apis.grading_methods import (
    get_effective_grading_method,
    get_system_default_grading_method,
    upsert_system_default_grading_method,
    upsert_tenant_grading_method,
)
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.dependencies.tenantDependency import get_db
from app.helpers.user_roles import (
    user_is_system_admin,
    user_requires_tenant_scope_for_data,
)
from app.models.role import UserRole
from app.models.user import User
from app.schemas.grading_method import (
    GradingMethodResponse,
    GradingMethodUpsertRequest,
)

grading_methods_router = APIRouter()


@grading_methods_router.get("/grading-methods", response_model=GradingMethodResponse)
def get_grading_method_endpoint(
    institution_id: Optional[int] = Query(None, description="Institution ID (system admins only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    target_institution_id = institution_id or current_user.institution_id
    if institution_id and institution_id != current_user.institution_id:
        if not user_is_system_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own institution's grading method",
            )

    if not target_institution_id and not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="institution_id is required",
        )

    return get_effective_grading_method(db, target_institution_id)


@grading_methods_router.put("/grading-methods", response_model=GradingMethodResponse)
def upsert_grading_method_endpoint(
    payload: GradingMethodUpsertRequest,
    institution_id: Optional[int] = Query(None, description="Institution ID (system admins only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    target_institution_id = institution_id or current_user.institution_id
    if user_requires_tenant_scope_for_data(current_user):
        target_institution_id = current_user.institution_id

    if not target_institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="institution_id is required",
        )

    ranges = [row.model_dump() for row in payload.grading_ranges]
    return upsert_tenant_grading_method(
        db=db,
        institution_id=target_institution_id,
        name=payload.name,
        ranges=ranges,
    )


@grading_methods_router.get(
    "/grading-methods/system-default",
    response_model=GradingMethodResponse,
)
def get_system_default_grading_method_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    _require_system_admin(current_user)
    return get_system_default_grading_method(db)


@grading_methods_router.put(
    "/grading-methods/system-default",
    response_model=GradingMethodResponse,
)
def upsert_system_default_grading_method_endpoint(
    payload: GradingMethodUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    _require_system_admin(current_user)
    ranges = [row.model_dump() for row in payload.grading_ranges]
    return upsert_system_default_grading_method(
        db=db,
        name=payload.name,
        ranges=ranges,
    )


def _require_system_admin(current_user: User) -> None:
    if not user_is_system_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can manage the platform default grading method",
        )
