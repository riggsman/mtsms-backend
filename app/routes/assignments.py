from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.assignments import (
    AssignmentRequest, AssignmentResponse, AssignmentUpdate,
    AssignmentSubmissionRequest, AssignmentSubmissionResponse
)
from app.apis.assignments import (
    create_assignment, get_assignment, get_assignments,
    update_assignment, delete_assignment,
    submit_assignment, get_student_submissions
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

assignment = APIRouter()

@assignment.post("/assignments", response_model=AssignmentResponse, status_code=201)
def create_assignment_endpoint(
    assignment_data: AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.TEACHER))
):
    """Create a new assignment"""
    # Set institution_id from current_user if not provided in request
    institution_id = assignment_data.institution_id
    if not institution_id and current_user.institution_id:
        institution_id = current_user.institution_id
    elif not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required to create an assignment")
    
    return create_assignment(db=db, assignment=assignment_data, institution_id=institution_id)

@assignment.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get an assignment by ID"""
    return get_assignment(db=db, assignment_id=assignment_id)

@assignment.get("/assignments", response_model=PaginatedResponse[AssignmentResponse])
def list_assignments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    course_code: Optional[str] = Query(None),
    lecturer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of assignments with pagination"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    # System admins (roles starting with 'system_') can see all assignments
    # Tenant users must filter by their institution_id
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view assignments")
    
    assignments, total = get_assignments(
        db=db,
        skip=skip,
        limit=page_size,
        course_code=course_code,
        institution_id=institution_id,
        lecturer_id=lecturer_id
    )
    return PaginatedResponse.create(
        items=assignments,
        total=total,
        page=page,
        page_size=page_size
    )

@assignment.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment_endpoint(
    assignment_id: int,
    assignment_update: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.TEACHER))
):
    """Update an assignment"""
    return update_assignment(db=db, assignment_id=assignment_id, assignment_update=assignment_update)

@assignment.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete an assignment (soft delete)"""
    delete_assignment(db=db, assignment_id=assignment_id)
    return None

@assignment.post("/assignments/submit", response_model=AssignmentSubmissionResponse, status_code=201)
def submit_assignment_endpoint(
    submission_data: AssignmentSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Submit an assignment (students can submit)"""
    return submit_assignment(db=db, submission=submission_data)

@assignment.get("/assignments/submissions/student/{student_id}", response_model=list[AssignmentSubmissionResponse])
def get_student_submissions_endpoint(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all submissions for a specific student"""
    return get_student_submissions(db=db, student_id=student_id)
