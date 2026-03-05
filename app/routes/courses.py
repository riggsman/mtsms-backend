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
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

course = APIRouter()

@course.post("/courses", response_model=CourseResponse, status_code=201)
def create_course_endpoint(
    course_data: CourseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    institution_id: Optional[int] = Depends(get_institution_id_from_header)
):
    """Create a new course - institution_id validated from header"""
    # Use institution_id from header (validated) or request body, fallback to user's institution_id
    final_institution_id = institution_id or course_data.institution_id or current_user.institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the X-Institution-Id header, request body, or ensure the user belongs to an institution")
    
    # Ensure request body institution_id matches header if both are provided
    if course_data.institution_id and institution_id and course_data.institution_id != institution_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution ID mismatch: header={institution_id}, body={course_data.institution_id}"
        )
    
    # Override request body with validated institution_id
    course_data.institution_id = final_institution_id
    
    return create_course(db=db, course=course_data, institution_id=final_institution_id, current_user=current_user)


@course.get("/courses/{course_id}", response_model=CourseResponse)
def get_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a course by ID"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return get_course(db=db, course_id=course_id, institution_id=institution_id)


@course.get("/courses", response_model=PaginatedResponse[CourseResponse])
def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    department_id: Optional[int] = Query(None),
    level_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
    institution_id: Optional[int] = Depends(get_institution_id_from_header)
):
    """Get list of courses with pagination - filtered by institution_id and tenant"""
    skip = (page - 1) * page_size
    
    # institution_id is validated by get_institution_id_from_header dependency
    # It ensures the header matches user's institution (unless system admin)
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
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return update_course(db=db, course_id=course_id, course_update=course_update, current_user=current_user, institution_id=institution_id)


@course.delete("/courses/{course_id}", status_code=204)
def delete_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN))
):
    """Delete a course (soft delete)"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    delete_course(db=db, course_id=course_id, current_user=current_user, institution_id=institution_id)
    return None