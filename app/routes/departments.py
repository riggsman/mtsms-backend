from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.departments import DepartmentRequest, DepartmentResponse, DepartmentUpdate
from app.apis.departments import (
    create_department, get_department, get_departments,
    update_department, delete_department
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, get_current_user, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.models.department import Department
from app.helpers.pagination import PaginatedResponse
from app.helpers.user_roles import user_is_system_admin

department_router = APIRouter()


# ============================================
# System Departments Endpoints (institution_id = 0)
# ============================================

@department_router.get("/departments/system", response_model=List[DepartmentResponse])
def list_system_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all system departments (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can view system departments")
    
    departments = db.query(Department).filter(Department.institution_id == 0).all()
    return departments


@department_router.post("/departments/system", response_model=DepartmentResponse, status_code=201)
def create_system_department(
    department_data: DepartmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new system department (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can create system departments")
    
    existing = db.query(Department).filter(
        Department.name == department_data.name,
        Department.institution_id == 0
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="System department with this name already exists")
    
    department_dict = department_data.model_dump(exclude={'institution_id'})
    department_dict['institution_id'] = 0
    new_department = Department(**department_dict)
    db.add(new_department)
    db.commit()
    db.refresh(new_department)
    return new_department


@department_router.post("/departments/{department_id}/copy", response_model=DepartmentResponse)
def copy_system_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Copy a system department to the current tenant's institution"""
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    system_dept = db.query(Department).filter(
        Department.id == department_id,
        Department.institution_id == 0
    ).first()
    
    if not system_dept:
        raise HTTPException(status_code=404, detail="System department not found")
    
    existing = db.query(Department).filter(
        Department.name == system_dept.name,
        Department.institution_id == institution_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Department already exists in your institution")
    
    new_dept = Department(
        name=system_dept.name,
        code=system_dept.code,
        description=system_dept.description,
        school_id=system_dept.school_id,
        head_id=None,
        institution_id=institution_id
    )
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    return new_dept


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
    page_size: int = Query(10, ge=1, le=1000),
    school_id: Optional[int] = Query(None, description="When set, only departments under this school/faculty"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of departments with pagination"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[list_departments] user_id={current_user.id}, role={current_user.role}, institution_id={current_user.institution_id}")
    
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    institution_id = None
    if current_user:
        is_system_admin = user_is_system_admin(current_user)
        logger.info(f"[list_departments] is_system_admin={is_system_admin}")
        if not is_system_admin:
            institution_id = current_user.institution_id
            logger.info(f"[list_departments] using institution_id={institution_id}")
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view departments")
    
    departments, total = get_departments(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        school_id=school_id,
    )
    logger.info(f"[list_departments] found {total} departments")
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
