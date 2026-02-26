from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.courses import CourseRequest, CourseResponse, CourseUpdate
from app.apis.courses import (
    create_course, get_course, get_courses,
    update_course, delete_course
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

course = APIRouter()

@course.post("/courses", response_model=CourseResponse, status_code=201)
def create_course_endpoint(
    course_data: CourseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Create a new course"""
    # Use institution_id from request body if provided, otherwise use current_user.institution_id
    institution_id = course_data.institution_id or current_user.institution_id
    
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    return create_course(db=db, course=course_data, institution_id=institution_id, current_user=current_user)


@course.get("/courses/{course_id}", response_model=CourseResponse)
def get_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a course by ID"""
    return get_course(db=db, course_id=course_id)


@course.get("/courses", response_model=PaginatedResponse[CourseResponse])
def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    department_id: Optional[int] = Query(None),
    level_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of courses with pagination"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    # System admins (roles starting with 'system_') can see all courses
    # Tenant users must filter by their institution_id
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view courses")
    
    courses, total = get_courses(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        department_id=department_id,
        level_id=level_id
    )
    return PaginatedResponse.create(
        items=courses,
        total=total,
        page=page,
        page_size=page_size
    )


@course.put("/courses/{course_id}", response_model=CourseResponse)
def update_course_endpoint(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.TEACHER))
):
    """Update a course"""
    return update_course(db=db, course_id=course_id, course_update=course_update, current_user=current_user)


@course.delete("/courses/{course_id}", status_code=204)
def delete_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN))
):
    """Delete a course (soft delete)"""
    delete_course(db=db, course_id=course_id, current_user=current_user)
    return None