from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.student import StudentRequest, StudentResponse, StudentUpdate
from app.apis.students import (
    create_student, get_student, get_students,
    update_student, delete_student
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

student = APIRouter()

@student.post("/students", response_model=StudentResponse, status_code=201)
def create_student_endpoint(
    student_data: StudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN)),
):
    """Create a new student"""
    # Use institution_id from request body if provided, otherwise use current_user.institution_id
    institution_id = student_data.institution_id or current_user.institution_id
    
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    return create_student(db=db, student=student_data, institution_id=institution_id, current_user=current_user)


@student.get("/students/{student_id}", response_model=StudentResponse)
def get_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a student by ID"""
    return get_student(db=db, student_id=student_id)


@student.get("/students", response_model=PaginatedResponse[StudentResponse])
def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    class_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    academic_year_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of students with pagination"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    # System admins (roles starting with 'system_') can see all students
    # Tenant users must filter by their institution_id
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view students")
    
    students, total = get_students(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        class_id=class_id,
        department_id=department_id,
        academic_year_id=academic_year_id
    )
    return PaginatedResponse.create(
        items=students,
        total=total,
        page=page,
        page_size=page_size
    )


@student.put("/students/{student_id}", response_model=StudentResponse)
def update_student_endpoint(
    student_id: int,
    student_update: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF))
):
    """Update a student"""
    return update_student(db=db, student_id=student_id, student_update=student_update, current_user=current_user)


@student.delete("/students/{student_id}", status_code=204)
def delete_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN))
):
    """Delete a student (soft delete)"""
    delete_student(db=db, student_id=student_id, current_user=current_user)
    return None