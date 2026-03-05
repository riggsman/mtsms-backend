from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
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
    is_system_admin = current_user.role and current_user.role.startswith("system_")
    institution_id = current_user.institution_id
    if is_system_admin:
        institution_id = assignment_data.institution_id or institution_id
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required to create an assignment")
    
    return create_assignment(db=db, assignment=assignment_data, institution_id=institution_id)

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

@assignment.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get an assignment by ID"""
    return get_assignment(db=db, assignment_id=assignment_id)

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
async def submit_assignment_endpoint(
    assignment_id: int = Form(...),
    student_id: str = Form(...),
    file: UploadFile = File(...),  # File upload is required
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Submit an assignment (students can submit)
    
    Requires file upload via multipart/form-data.
    Files are saved to the filesystem and only the file URL is stored in the database.
    """
    from app.helpers.file_upload import save_uploaded_file, get_file_url
    from app.apis.uploads import get_tenant_domain
    from fastapi import HTTPException, status
    
    # Get assignment to verify it exists and get institution_id
    assignment = get_assignment(db, assignment_id)
    institution_id = assignment.institution_id
    
    # Get tenant domain for file prefixing
    tenant_domain = get_tenant_domain(institution_id)
    
    # Save uploaded file to filesystem
    file_path, relative_path = await save_uploaded_file(
        file=file,
        tenant_domain=tenant_domain,
        file_category='assignments'
    )
    
    # Generate file URL for database storage (only URL, not file data)
    file_url = get_file_url(relative_path, base_url="/api/v1/uploads")
    
    # Create submission request with file URL only
    submission_request = AssignmentSubmissionRequest(
        assignment_id=assignment_id,
        student_id=student_id,
        submission_file=file_url,  # Store only the URL, not file data
        note=note
    )
    
    return submit_assignment(db=db, submission=submission_request)

@assignment.get("/assignments/submissions/student/{student_id}", response_model=list[AssignmentSubmissionResponse])
def get_student_submissions_endpoint(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all submissions for a specific student"""
    submissions = get_student_submissions(db=db, student_id=student_id)
    # Map fields to match frontend expectations
    result = []
    for sub in submissions:
        submission_dict = {
            "id": sub.id,
            "assignment_id": sub.assignment_id,
            "student_id": sub.student_id,
            "submission_file": sub.submission_file,
            "submission_date": sub.submission_date,
            "submitted_at": sub.submission_date,  # Alias for frontend
            "status": sub.status,
            "grade": sub.grade,
            "score": None,  # Convert grade to score if numeric
            "feedback": sub.feedback,
            "note": getattr(sub, 'note', None) or sub.feedback,  # Use note or fallback to feedback
            "created_at": sub.created_at,
            "updated_at": sub.updated_at
        }
        # Convert grade to score if grade is numeric
        if sub.grade:
            try:
                submission_dict['score'] = float(sub.grade)
            except (ValueError, TypeError):
                pass
        result.append(submission_dict)
    return result
