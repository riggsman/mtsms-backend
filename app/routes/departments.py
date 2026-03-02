from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.departments import DepartmentRequest, DepartmentResponse, DepartmentUpdate
from app.apis.departments import (
    create_department, get_department, get_departments,
    update_department, delete_department
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

department_router = APIRouter()


@department_router.post("/departments", response_model=DepartmentResponse, status_code=201)
def create_department_endpoint(
    department_data: DepartmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Create a new department"""
    institution_id = department_data.institution_id or current_user.institution_id
    
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    return create_department(db=db, department=department_data, institution_id=institution_id, current_user=current_user)


@department_router.get("/departments/{department_id}", response_model=DepartmentResponse)
def get_department_endpoint(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a department by ID"""
    return get_department(db=db, department_id=department_id)


@department_router.get("/departments", response_model=PaginatedResponse[DepartmentResponse])
def list_departments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of departments with pagination"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view departments")
    
    departments, total = get_departments(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id
    )
    return PaginatedResponse.create(
        items=departments,
        total=total,
        page=page,
        page_size=page_size
    )


@department_router.put("/departments/{department_id}", response_model=DepartmentResponse)
def update_department_endpoint(
    department_id: int,
    department_update: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update a department"""
    return update_department(db=db, department_id=department_id, department_update=department_update, current_user=current_user)


@department_router.delete("/departments/{department_id}", status_code=204)
def delete_department_endpoint(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a department (soft delete)"""
    delete_department(db=db, department_id=department_id, current_user=current_user)
    return None
