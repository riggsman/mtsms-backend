from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from app.schemas.complaints import ComplaintRequest, ComplaintResponse, ComplaintUpdate
from app.apis.complaints import (
    create_complaint, get_complaint, get_complaints,
    update_complaint, delete_complaint, get_student_complaints
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

complaint = APIRouter()

@complaint.post("/complaints", response_model=ComplaintResponse, status_code=201)
async def create_complaint_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Create a new complaint (students can create complaints)
    
    Requires FormData with file uploads for screenshots.
    Files are saved to the filesystem and only file URLs are stored in the database.
    """
    from app.helpers.file_upload import save_uploaded_file, get_file_url
    from app.apis.uploads import get_tenant_domain
    from fastapi import HTTPException, status
    
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to create complaints"
        )
    
    # Check content type - must be FormData for file uploads
    content_type = request.headers.get("content-type", "")
    
    if "multipart/form-data" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request must be multipart/form-data for file uploads"
        )
    
    # Handle FormData request
    form_data = await request.form()
    
    # Get form fields
    student_id = form_data.get("student_id", current_user.id)
    complaint_type = form_data.get("complaint_type", "")
    caption = form_data.get("caption", "")
    contents = form_data.get("contents", "")
    is_anonymous = form_data.get("is_anonymous", "false").lower() == "true"
    
    # Process uploaded screenshot files only (no base64)
    screenshot_urls = []
    screenshot_files = form_data.getlist("screenshots")
    if screenshot_files:
        tenant_domain = get_tenant_domain(current_user.institution_id)
        for screenshot_file in screenshot_files:
            if hasattr(screenshot_file, 'file'):  # It's an UploadFile
                file_path, relative_path = await save_uploaded_file(
                    file=screenshot_file,
                    tenant_domain=tenant_domain,
                    file_category='complaints'
                )
                file_url = get_file_url(relative_path, base_url="/api/v1/uploads")
                screenshot_urls.append(file_url)  # Store only URLs, not file data
    
    # Create complaint request from FormData
    complaint_request = ComplaintRequest(
        student_id=str(student_id),
        complaint_type=complaint_type,
        caption=caption,
        contents=contents,
        is_anonymous=is_anonymous,
        screenshots=screenshot_urls if screenshot_urls else None
    )
    
    return create_complaint(
        db=db,
        complaint=complaint_request,
        institution_id=current_user.institution_id,
        current_user=current_user
    )

@complaint.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
def get_complaint_endpoint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a complaint by ID"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return get_complaint(db=db, complaint_id=complaint_id, institution_id=institution_id)

@complaint.get("/complaints", response_model=PaginatedResponse[ComplaintResponse])
def list_complaints(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    student_id: Optional[str] = Query(None),
    complaint_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Get list of complaints with pagination (admin/staff/secretary only)"""
    skip = (page - 1) * page_size
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    complaints, total = get_complaints(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        student_id=student_id,
        complaint_type=complaint_type,
        status=status
    )
    return PaginatedResponse.create(
        items=complaints,
        total=total,
        page=page,
        page_size=page_size
    )

@complaint.get("/complaints/student/{student_id}", response_model=list[ComplaintResponse])
def get_student_complaints_endpoint(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all complaints for a specific student"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return get_student_complaints(db=db, student_id=student_id, institution_id=institution_id)

@complaint.put("/complaints/{complaint_id}", response_model=ComplaintResponse)
def update_complaint_endpoint(
    complaint_id: int,
    complaint_update: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Update a complaint (mark as addressed)"""
    # Auto-fill resolver info if marking as addressed
    if complaint_update.status == 'addressed':
        if not complaint_update.resolved_by:
            complaint_update.resolved_by = f"{current_user.firstname} {current_user.lastname}"
        if not complaint_update.resolver_role:
            complaint_update.resolver_role = current_user.role
    
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    return update_complaint(db=db, complaint_id=complaint_id, complaint_update=complaint_update, institution_id=institution_id)

@complaint.delete("/complaints/{complaint_id}", status_code=204)
def delete_complaint_endpoint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a complaint (soft delete)"""
    institution_id = None
    if current_user and current_user.role and not current_user.role.startswith("system_"):
        institution_id = current_user.institution_id
    delete_complaint(db=db, complaint_id=complaint_id, institution_id=institution_id)
    return None
