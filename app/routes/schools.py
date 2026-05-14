"""
School Routes - FastAPI endpoints for schools and school fees
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, get_current_user, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.models.school import School
from app.schemas.school import (
    SchoolCreate,
    SchoolUpdate,
    SchoolResponse,
    SchoolFeeCreate,
    SchoolFeeUpdate,
    SchoolFeeResponse,
    SchoolWithFeesResponse
)
from app.schemas.fee_structure import (
    FeeInstallmentCreate,
    FeeInstallmentUpdate,
    FeeInstallmentResponse
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
from app.apis.fee_structure import (
    get_installments,
    get_installment_by_id,
    create_installment,
    update_installment,
    delete_installment
)
from app.helpers.user_roles import user_is_system_admin

router = APIRouter()


def require_institution(current_user: User):
    """Helper to require user to belong to an institution"""
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    return current_user.institution_id


# ============================================
# System Schools Endpoints (institution_id = 0)
# ============================================

@router.get("/schools/system", response_model=List[SchoolResponse])
def list_system_schools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all system schools (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can view system schools")
    
    schools = db.query(School).filter(School.institution_id == 0).all()
    return schools


@router.post("/schools/system", response_model=SchoolResponse, status_code=201)
def create_system_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new system school (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can create system schools")
    
    existing = db.query(School).filter(
        School.name == payload.name,
        School.institution_id == 0
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="System school with this name already exists")
    
    school_data = payload.model_dump()
    school_data['institution_id'] = 0
    new_school = School(**school_data)
    db.add(new_school)
    db.commit()
    db.refresh(new_school)
    return new_school


@router.post("/schools/{school_id}/copy", response_model=SchoolResponse)
def copy_system_school(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Copy a system school to the current tenant's institution"""
    # Allow any authenticated user to copy
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    # Get the system school
    system_school = db.query(School).filter(
        School.id == school_id,
        School.institution_id == 0
    ).first()
    
    if not system_school:
        raise HTTPException(status_code=404, detail="System school not found")
    
    # Check if already copied
    existing = db.query(School).filter(
        School.name == system_school.name,
        School.institution_id == institution_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="School already exists in your institution")
    
    # Create copy for tenant
    new_school = School(
        name=system_school.name,
        code=system_school.code,
        description=system_school.description,
        is_active=system_school.is_active,
        sort_order=system_school.sort_order,
        institution_id=institution_id
    )
    db.add(new_school)
    db.commit()
    db.refresh(new_school)
    return new_school


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
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get fees for a school, optionally filtered by level"""
    institution_id = require_institution(current_user)
    fees = get_school_fees(db, school_id, institution_id, level)
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


# ============================================
# School Installment Endpoints
# ============================================

@router.get("/schools/{school_id}/installments", response_model=List[FeeInstallmentResponse])
def list_school_installments(
    school_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get all active installments for a specific school.
    """
    institution_id = require_institution(current_user)
    # Verify school belongs to institution
    school = get_school_by_id(db, school_id, institution_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    installments = get_installments(db, institution_id, school_id)
    return [FeeInstallmentResponse.from_installment(i) for i in installments]


@router.post("/schools/{school_id}/installments", response_model=FeeInstallmentResponse, status_code=201)
def create_school_installment(
    school_id: int,
    installment_data: FeeInstallmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.SECRETARY
    ))
):
    """
    Create a new fee installment for a specific school.
    Admin, Super Admin, or Secretary only.
    """
    institution_id = require_institution(current_user)
    # Verify school belongs to institution
    school = get_school_by_id(db, school_id, institution_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Override school_id with the path parameter
    installment_data.school_id = school_id
    
    installment = create_installment(db, institution_id, installment_data)
    return FeeInstallmentResponse.from_installment(installment)


@router.get("/schools/{school_id}/installments/{installment_id}", response_model=FeeInstallmentResponse)
def get_school_installment(
    school_id: int,
    installment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get a specific installment by ID for a school.
    """
    institution_id = require_institution(current_user)
    # Verify school belongs to institution
    school = get_school_by_id(db, school_id, institution_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    installment = get_installment_by_id(db, installment_id, institution_id, school_id)
    return FeeInstallmentResponse.from_installment(installment)


@router.put("/schools/{school_id}/installments/{installment_id}", response_model=FeeInstallmentResponse)
def update_school_installment(
    school_id: int,
    installment_id: int,
    installment_data: FeeInstallmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.SECRETARY
    ))
):
    """
    Update an existing fee installment for a school.
    Admin, Super Admin, or Secretary only.
    """
    institution_id = require_institution(current_user)
    # Verify school belongs to institution
    school = get_school_by_id(db, school_id, institution_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    installment = update_installment(db, institution_id, installment_id, installment_data, school_id)
    return FeeInstallmentResponse.from_installment(installment)


@router.delete("/schools/{school_id}/installments/{installment_id}", status_code=204)
def delete_school_installment(
    school_id: int,
    installment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN
    ))
):
    """
    Delete a fee installment (soft delete - marks as inactive).
    Super Admin only.
    """
    institution_id = require_institution(current_user)
    # Verify school belongs to institution
    school = get_school_by_id(db, school_id, institution_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    delete_installment(db, institution_id, installment_id, school_id)
    return None
