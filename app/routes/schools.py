"""
School Routes - FastAPI endpoints for schools and school fees
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.schemas.school import (
    SchoolCreate,
    SchoolUpdate,
    SchoolResponse,
    SchoolFeeCreate,
    SchoolFeeUpdate,
    SchoolFeeResponse,
    SchoolWithFeesResponse
)
from app.apis.school import (
    get_schools,
    get_school_by_id,
    create_school,
    update_school,
    delete_school,
    get_school_fees,
    get_school_fee_by_id,
    create_or_update_school_fee,
    update_school_fee,
    delete_school_fee,
    get_all_schools_with_fees
)

router = APIRouter()


def require_institution(current_user: User):
    """Helper to require user to belong to an institution"""
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    return current_user.institution_id


# ============================================
# School Endpoints
# ============================================

@router.get("/schools", response_model=List[SchoolWithFeesResponse])
def list_schools(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all schools for the current user's institution"""
    institution_id = require_institution(current_user)
    schools = get_all_schools_with_fees(db, institution_id)
    return schools


@router.post("/schools", response_model=SchoolResponse, status_code=201)
def create_school_endpoint(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Create a new school (Admin/Super Admin only)"""
    institution_id = require_institution(current_user)
    school = create_school(db, institution_id, payload)
    return school


@router.get("/schools/{school_id}", response_model=SchoolWithFeesResponse)
def get_school_endpoint(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a specific school with its fees"""
    institution_id = require_institution(current_user)
    school = get_school_by_id(db, school_id, institution_id)
    fees = get_school_fees(db, school_id, institution_id)
    
    return {
        "id": school.id,
        "institution_id": school.institution_id,
        "name": school.name,
        "code": school.code,
        "description": school.description,
        "is_active": school.is_active,
        "sort_order": school.sort_order,
        "fees": [SchoolFeeResponse.from_model(f) for f in fees],
        "created_at": school.created_at,
        "updated_at": school.updated_at
    }


@router.put("/schools/{school_id}", response_model=SchoolResponse)
def update_school_endpoint(
    school_id: int,
    payload: SchoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update a school (Admin/Super Admin only)"""
    institution_id = require_institution(current_user)
    school = update_school(db, school_id, institution_id, payload)
    return school


@router.delete("/schools/{school_id}", status_code=204)
def delete_school_endpoint(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a school and its fees (Super Admin only)"""
    institution_id = require_institution(current_user)
    delete_school(db, school_id, institution_id)
    return None


# ============================================
# School Fee Endpoints
# ============================================

@router.get("/schools/{school_id}/fees", response_model=List[SchoolFeeResponse])
def list_school_fees(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all fees for a school"""
    institution_id = require_institution(current_user)
    fees = get_school_fees(db, school_id, institution_id)
    return [SchoolFeeResponse.from_model(f) for f in fees]


@router.post("/schools/{school_id}/fees", response_model=SchoolFeeResponse, status_code=201)
def create_or_update_school_fee_endpoint(
    school_id: int,
    payload: SchoolFeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Create or update a school fee (upsert by school_id + level).
    If a fee already exists for this school + level, it will be updated.
    """
    institution_id = require_institution(current_user)
    fee = create_or_update_school_fee(db, school_id, institution_id, payload)
    return SchoolFeeResponse.from_model(fee)


@router.put("/schools/{school_id}/fees/{fee_id}", response_model=SchoolFeeResponse)
def update_school_fee_endpoint(
    school_id: int,
    fee_id: int,
    payload: SchoolFeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update a school fee"""
    institution_id = require_institution(current_user)
    fee = update_school_fee(db, fee_id, institution_id, payload)
    return SchoolFeeResponse.from_model(fee)


@router.delete("/schools/{school_id}/fees/{fee_id}", status_code=204)
def delete_school_fee_endpoint(
    school_id: int,
    fee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a school fee"""
    institution_id = require_institution(current_user)
    delete_school_fee(db, fee_id, institution_id)
    return None


# ============================================
# Bulk Fee Operations
# ============================================

@router.post("/schools/{school_id}/fees/bulk", response_model=List[SchoolFeeResponse], status_code=201)
def bulk_create_fees(
    school_id: int,
    fees: List[SchoolFeeCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Create or update multiple fees for a school at once.
    Useful for setting up fees for all levels (HND, DEGREE, MASTERS) in one call.
    """
    institution_id = require_institution(current_user)
    result = []
    
    for fee_data in fees:
        fee = create_or_update_school_fee(db, school_id, institution_id, fee_data)
        result.append(SchoolFeeResponse.from_model(fee))
    
    return result
