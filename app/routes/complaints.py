from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
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
def create_complaint_endpoint(
    complaint_data: ComplaintRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Create a new complaint (students can create complaints)"""
    return create_complaint(db=db, complaint=complaint_data)

@complaint.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
def get_complaint_endpoint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a complaint by ID"""
    return get_complaint(db=db, complaint_id=complaint_id)

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
    complaints, total = get_complaints(
        db=db,
        skip=skip,
        limit=page_size,
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
    return get_student_complaints(db=db, student_id=student_id)

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
    
    return update_complaint(db=db, complaint_id=complaint_id, complaint_update=complaint_update)

@complaint.delete("/complaints/{complaint_id}", status_code=204)
def delete_complaint_endpoint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a complaint (soft delete)"""
    delete_complaint(db=db, complaint_id=complaint_id)
    return None
