from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.schemas.courses import CoursePerformanceResponse, CourseRequest, CourseResponse, CourseUpdate
from app.apis.courses import (
    create_course, get_course, get_courses,
    update_course, delete_course
)
from app.services.course_performance import build_course_performance, list_course_performance
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, get_current_user, require_any_role
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.models.user import User
from app.models.role import UserRole
from app.models.course import Course as CourseModel
from app.helpers.pagination import PaginatedResponse
from app.helpers.user_roles import user_requires_tenant_scope_for_data, user_is_system_admin

course = APIRouter()


# ============================================
# System Courses Endpoints (institution_id = 0)
# ============================================

@course.get("/courses/system", response_model=List[CourseResponse])
def list_system_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all system courses (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can view system courses")
    
    courses = db.query(CourseModel).filter(CourseModel.institution_id == 0).all()
    return courses


@course.post("/courses/system", response_model=CourseResponse, status_code=201)
def create_system_course(
    course_data: CourseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new system course (institution_id = 0) - System Admin only"""
    if not user_is_system_admin(current_user):
        raise HTTPException(status_code=403, detail="Only system admin can create system courses")
    
    existing = db.query(CourseModel).filter(
        CourseModel.name == course_data.name,
        CourseModel.institution_id == 0
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="System course with this name already exists")
    
    course_dict = course_data.model_dump(exclude={'institution_id'})
    course_dict['institution_id'] = 0
    new_course = CourseModel(**course_dict)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@course.post("/courses/{course_id}/copy", response_model=CourseResponse)
def copy_system_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Copy a system course to the current tenant's institution"""
    institution_id = current_user.institution_id
    if not institution_id:
        raise HTTPException(status_code=400, detail="User must belong to an institution")
    
    system_course = db.query(CourseModel).filter(
        CourseModel.id == course_id,
        CourseModel.institution_id == 0
    ).first()
    
    if not system_course:
        raise HTTPException(status_code=404, detail="System course not found")
    
    existing = db.query(CourseModel).filter(
        CourseModel.name == system_course.name,
        CourseModel.institution_id == institution_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Course already exists in your institution")
    
    new_course = CourseModel(
        name=system_course.name,
        code=system_course.code,
        description=system_course.description,
        department_id=system_course.department_id,
        specialization_id=system_course.specialization_id,
        school_id=system_course.school_id,
        credit_units=system_course.credit_units,
        is_core=system_course.is_core,
        is_elective=system_course.is_elective,
        level=system_course.level,
        semester=system_course.semester,
        institution_id=institution_id
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

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


@course.get("/courses/performance", response_model=List[CoursePerformanceResponse])
def list_course_performance_endpoint(
    department_id: Optional[int] = Query(None),
    semester: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.TEACHER)),
    institution_id: Optional[int] = Depends(get_institution_id_from_header)
):
    """Get course performance metrics for the current tenant."""
    final_institution_id = institution_id
    if current_user and user_requires_tenant_scope_for_data(current_user):
        final_institution_id = current_user.institution_id
    return list_course_performance(
        db=db,
        institution_id=final_institution_id,
        department_id=department_id,
        semester=semester,
    )


@course.get("/courses/{course_id}/performance", response_model=CoursePerformanceResponse)
def get_course_performance_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.TEACHER))
):
    """Get performance metrics for one course."""
    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    course_obj = get_course(db=db, course_id=course_id, institution_id=institution_id)
    return build_course_performance(db=db, course=course_obj)


@course.get("/courses/{course_id}", response_model=CourseResponse)
def get_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a course by ID"""
    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    return get_course(db=db, course_id=course_id, institution_id=institution_id)


@course.get("/courses", response_model=PaginatedResponse[CourseResponse])
def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=10000),
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
    current_user: User = Depends(
        require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.TEACHER)
    ),
):
    """Update a course"""
    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    return update_course(db=db, course_id=course_id, course_update=course_update, current_user=current_user, institution_id=institution_id)


@course.patch("/courses/{course_id}", response_model=CourseResponse)
def patch_course_endpoint(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.TEACHER)
    ),
):
    """Partially update a course."""
    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    return update_course(db=db, course_id=course_id, course_update=course_update, current_user=current_user, institution_id=institution_id)


@course.delete("/courses/{course_id}", status_code=204)
def delete_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
):
    """Delete a course (soft delete)"""
    institution_id = None
    if current_user and user_requires_tenant_scope_for_data(current_user):
        institution_id = current_user.institution_id
    delete_course(db=db, course_id=course_id, current_user=current_user, institution_id=institution_id)
    return None
