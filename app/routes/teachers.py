from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.teachers import TeacherRequest, TeacherResponse, TeacherUpdate
from app.apis.teachers import (
    create_teacher,
    get_teacher,
    get_teachers,
    update_teacher,
    delete_teacher,
    teacher_to_response,
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse
from app.helpers.branch_scope import effective_branch_scope_id
from app.helpers.user_roles import user_is_system_admin

teacher = APIRouter()

@teacher.post("/teachers", response_model=TeacherResponse, status_code=201)
def create_teacher_endpoint(
    teacher_data: TeacherRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Create a new teacher and automatically create a user account with staff role"""
    # Set institution_id from current_user if not provided
    if not teacher_data.institution_id and current_user:
        teacher_data.institution_id = current_user.institution_id
    
    if not teacher_data.institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    created = create_teacher(db=db, teacher=teacher_data, current_user=current_user)
    return teacher_to_response(db, created)


@teacher.get("/teachers/{teacher_id}", response_model=TeacherResponse)
def get_teacher_endpoint(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a teacher by ID"""
    t = get_teacher(db=db, teacher_id=teacher_id)
    return teacher_to_response(db, t)


@teacher.get("/teachers", response_model=PaginatedResponse[TeacherResponse])
def list_teachers(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    institution_id: Optional[int] = Query(None, description="Filter by institution ID"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of teachers with pagination, filtered by institution_id"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    # If provided as query parameter, use it; otherwise use current user's institution_id
    final_institution_id = institution_id
    if final_institution_id is None and current_user:
        is_system_admin = user_is_system_admin(current_user)
        if not is_system_admin:
            final_institution_id = current_user.institution_id
            if not final_institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view teachers")
    
    # For non-system admins, ensure institution_id is set
    if current_user:
        is_system_admin = user_is_system_admin(current_user)
        if not is_system_admin and not final_institution_id:
            from app.exceptions import ValidationError
            raise ValidationError("institution_id is required to fetch teachers")
    
    branch_scope = effective_branch_scope_id(db, current_user)

    teachers, total = get_teachers(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=final_institution_id,
        department_id=department_id,
        branch_id=branch_scope,
    )
    return PaginatedResponse.create(
        items=[teacher_to_response(db, row) for row in teachers],
        total=total,
        page=page,
        page_size=page_size
    )


@teacher.put("/teachers/{teacher_id}", response_model=TeacherResponse)
def update_teacher_endpoint(
    teacher_id: int,
    teacher_update: TeacherUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN))
):
    """Update a teacher"""
    updated = update_teacher(
        db=db,
        teacher_id=teacher_id,
        teacher_update=teacher_update,
        current_user=current_user,
    )
    return teacher_to_response(db, updated)


@teacher.delete("/teachers/{teacher_id}", status_code=204)
def delete_teacher_endpoint(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """Delete a teacher (soft delete)"""
    delete_teacher(db=db, teacher_id=teacher_id, current_user=current_user)
    return None