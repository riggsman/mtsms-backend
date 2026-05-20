from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.specializations import SpecializationRequest, SpecializationResponse, SpecializationUpdate
from app.apis.specializations import (
    create_specialization, get_specialization, get_specializations,
    update_specialization, delete_specialization
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, get_current_user, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.models.specialty import Specialization
from app.models.department import Department
from app.helpers.pagination import PaginatedResponse
from app.helpers.user_roles import user_is_system_admin
from app.helpers.tenant_scope import institution_id_for_user
from app.dependencies.institutionDependency import get_institution_id_from_header

specialization_router = APIRouter()


# ============================================
# System Specializations Endpoints (institution_id = 0)
# ============================================

@specialization_router.get("/specializations/system", response_model=List[SpecializationResponse])
def list_system_specializations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all system specializations (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can view system specializations")
    
    specializations = db.query(Specialization).filter(Specialization.institution_id == 0).all()
    return specializations


@specialization_router.post("/specializations/system", response_model=SpecializationResponse, status_code=201)
def create_system_specialization(
    specialization_data: SpecializationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new system specialization (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can create system specializations")
    
    if not specialization_data.department_id:
        raise HTTPException(status_code=400, detail="department_id is required")
    
    department = db.query(Department).filter(
        Department.id == specialization_data.department_id,
        Department.deleted_at.is_(None)
    ).first()
    
    if not department:
        raise HTTPException(status_code=400, detail="Department not found")
    
    if department.institution_id != 0:
        raise HTTPException(status_code=400, detail="Department must belong to the system (institution_id = 0)")
    
    existing = db.query(Specialization).filter(
        Specialization.name == specialization_data.name,
        Specialization.institution_id == 0
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="System specialization with this name already exists")
    
    spec_dict = specialization_data.model_dump(exclude={'institution_id'})
    spec_dict['institution_id'] = 0
    new_spec = Specialization(**spec_dict)
    db.add(new_spec)
    db.commit()
    db.refresh(new_spec)
    return new_spec


@specialization_router.post("/specializations/{specialization_id}/copy", response_model=SpecializationResponse)
def copy_system_specialization(
    specialization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Copy a system specialization to the current tenant's institution"""
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    system_spec = db.query(Specialization).filter(
        Specialization.id == specialization_id,
        Specialization.institution_id == 0
    ).first()
    
    if not system_spec:
        raise HTTPException(status_code=404, detail="System specialization not found")
    
    existing = db.query(Specialization).filter(
        Specialization.name == system_spec.name,
        Specialization.institution_id == institution_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Specialization already exists in your institution")
    
    new_spec = Specialization(
        name=system_spec.name,
        code=system_spec.code,
        description=system_spec.description,
        department_id=system_spec.department_id,
        head_id=None,
        institution_id=institution_id
    )
    db.add(new_spec)
    db.commit()
    db.refresh(new_spec)
    return new_spec


@specialization_router.post("/specializations", response_model=SpecializationResponse, status_code=201)
def create_specialization_endpoint(
    specialization_data: SpecializationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Create a new specialization"""
    if not specialization_data.department_id:
        raise HTTPException(status_code=400, detail="department_id is required")
    
    department = db.query(Department).filter(
        Department.id == specialization_data.department_id,
        Department.deleted_at.is_(None)
    ).first()
    
    if not department:
        raise HTTPException(status_code=400, detail="Department not found")
    
    institution_id = specialization_data.institution_id or current_user.institution_id
    
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    if department.institution_id != institution_id:
        raise HTTPException(status_code=400, detail="Department must belong to your institution")
    
    return create_specialization(db=db, specialization=specialization_data, institution_id=institution_id, current_user=current_user)


@specialization_router.get("/specializations/{specialization_id}", response_model=SpecializationResponse)
def get_specialization_endpoint(
    specialization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Get a specialization by ID"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    return get_specialization(db=db, specialization_id=specialization_id, institution_id=institution_id)


@specialization_router.get("/specializations", response_model=PaginatedResponse[SpecializationResponse])
def list_specializations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of specializations with pagination"""
    from app.helpers.user_roles import user_is_system_admin
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[list_specializations] user_id={current_user.id}, role={current_user.role}, institution_id={current_user.institution_id}")
    
    skip = (page - 1) * page_size
    
    institution_id = None
    if current_user:
        is_system_admin = user_is_system_admin(current_user)
        logger.info(f"[list_specializations] is_system_admin={is_system_admin}")
        if not is_system_admin:
            institution_id = current_user.institution_id
            logger.info(f"[list_specializations] using institution_id={institution_id}")
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view specializations")
    
    specializations, total = get_specializations(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        department_id=department_id
    )
    logger.info(f"[list_specializations] found {total} specializations")
    return PaginatedResponse.create(
        items=specializations,
        total=total,
        page=page,
        page_size=page_size
    )


@specialization_router.put("/specializations/{specialization_id}", response_model=SpecializationResponse)
def update_specialization_endpoint(
    specialization_id: int,
    specialization_update: SpecializationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Update a specialization"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    return update_specialization(db=db, specialization_id=specialization_id, specialization_update=specialization_update, current_user=current_user, institution_id=institution_id)


@specialization_router.delete("/specializations/{specialization_id}", status_code=204)
def delete_specialization_endpoint(
    specialization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Delete a specialization (soft delete)"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    delete_specialization(db=db, specialization_id=specialization_id, current_user=current_user, institution_id=institution_id)
    return None
