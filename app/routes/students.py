from fastapi import APIRouter, Depends, Header, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.student import StudentRequest, StudentResponse, StudentUpdate
from app.apis.students import (
    create_student, get_student, get_students,
    update_student, delete_student
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.models.user import User
from app.models.role import UserRole
from app.models.student import Student
from app.helpers.pagination import PaginatedResponse

student = APIRouter()

# IMPORTANT: More specific routes must be defined BEFORE parameterized routes
# This ensures FastAPI matches /students/me before /students/{student_id}

@student.get("/students/me", response_model=StudentResponse)
def get_current_student(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Get the current user's student record (for students only)
    This route must be defined BEFORE /students/{student_id} to avoid route conflicts
    """
    if current_user.role != 'student':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for students"
        )
    
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution"
        )
    
    # Try to find student by email first
    student = db.query(Student).filter(
        Student.email == current_user.email,
        Student.institution_id == current_user.institution_id,
        Student.deleted_at.is_(None)
    ).first()
    
    # If not found by email, try by user ID (if student.id matches user.id)
    if not student and current_user.id:
        student = db.query(Student).filter(
            Student.id == current_user.id,
            Student.institution_id == current_user.institution_id,
            Student.deleted_at.is_(None)
        ).first()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student record not found for current user"
        )
    
    return StudentResponse.model_validate(student, from_attributes=True)

@student.post("/students", response_model=StudentResponse, status_code=201)
def create_student_endpoint(
    student_data: StudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN)),
    institution_id: Optional[int] = Depends(get_institution_id_from_header)
):
    """Create a new student - institution_id validated from header"""
    # Use institution_id from header (validated) or request body, fallback to user's institution_id
    final_institution_id = institution_id or student_data.institution_id or current_user.institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the X-Institution-Id header, request body, or ensure the user belongs to an institution")
    
    # Ensure request body institution_id matches header if both are provided
    if student_data.institution_id and institution_id and student_data.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution ID mismatch: header={institution_id}, body={student_data.institution_id}"
        )
    
    # Override request body with validated institution_id
    student_data.institution_id = final_institution_id
    
    return create_student(db=db, student=student_data, institution_id=final_institution_id, current_user=current_user)

@student.get("/students", response_model=PaginatedResponse[StudentResponse])
def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    class_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    academic_year_id: Optional[int] = Query(None),
    x_institution_id: Optional[str] = Header(default=None, alias="X-Institution-Id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of students with pagination - filtered by institution_id and tenant"""
    skip = (page - 1) * page_size
    
    # Validate and extract institution_id from header
    is_system_admin = current_user.role and current_user.role.startswith('system_')
    institution_id = None
    
    if is_system_admin:
        # System admins can access any institution or all institutions
        if x_institution_id:
            try:
                institution_id = int(x_institution_id)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid institution_id format: {x_institution_id}"
                )
        # If no header, institution_id remains None (can access all)
    else:
        # Non-system users must belong to an institution
        if not current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an institution to view students"
            )
        
        # If header is provided, validate it matches user's institution
        if x_institution_id:
            try:
                header_institution_id = int(x_institution_id)
                if header_institution_id != current_user.institution_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Institution ID mismatch. You can only access data for your institution (ID: {current_user.institution_id})"
                    )
                institution_id = header_institution_id
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid institution_id format: {x_institution_id}"
                )
        else:
            # No header provided - use user's institution_id
            institution_id = current_user.institution_id
    
    # institution_id is validated - use for tenant isolation
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

@student.get("/students/{student_id}", response_model=StudentResponse)
def get_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a student by ID (tenant-scoped)"""
    # Determine institution_id for filtering
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return get_student(db=db, student_id=student_id, institution_id=institution_id)

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
    current_user: User = Depends(require_any_role(UserRole.ADMIN,UserRole.SUPER_ADMIN))
):
    """Delete a student (soft delete)"""
    delete_student(db=db, student_id=student_id, current_user=current_user)
    return None

# @student.delete("/admin/students/{student_id}", status_code=204)
# def delete_student_endpoint(
#     student_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(require_any_role(UserRole.ADMIN))
# ):
#     """Delete a student (soft delete)"""
#     delete_student(db=db, student_id=student_id, current_user=current_user)
#     return None