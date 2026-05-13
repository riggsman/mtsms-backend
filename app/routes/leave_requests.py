from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse
from app.apis.leave_request import (
    create_leave_request, get_leave_requests, get_leave_request_by_id,
    update_leave_request, approve_leave_request, reject_leave_request, delete_leave_request,
    get_pending_leave_count
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

leave_router = APIRouter()

@leave_router.post("/leave-requests", response_model=LeaveRequestResponse, status_code=201)
def create_leave_request_endpoint(
    leave_data: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Create a new leave request"""
    return create_leave_request(db=db, leave_data=leave_data, institution_id=current_user.institution_id, user_id=current_user.id)

@leave_router.get("/leave-requests", response_model=PaginatedResponse)
def get_leave_requests_endpoint(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all leave requests for the institution"""
    return get_leave_requests(db=db, institution_id=current_user.institution_id, status=status, page=page, page_size=page_size)

@leave_router.get("/leave-requests/{leave_id}", response_model=LeaveRequestResponse)
def get_leave_request_endpoint(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a specific leave request"""
    leave = get_leave_request_by_id(db=db, leave_id=leave_id, institution_id=current_user.institution_id)
    if not leave:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Leave request not found")
    return leave

@leave_router.put("/leave-requests/{leave_id}", response_model=LeaveRequestResponse)
def update_leave_request_endpoint(
    leave_id: int,
    leave_data: LeaveRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update a leave request (admin only)"""
    leave = update_leave_request(db=db, leave_id=leave_id, leave_data=leave_data, institution_id=current_user.institution_id)
    if not leave:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Leave request not found")
    return leave

@leave_router.post("/leave-requests/{leave_id}/approve", response_model=LeaveRequestResponse)
def approve_leave_request_endpoint(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Approve a leave request (admin only)"""
    leave = approve_leave_request(db=db, leave_id=leave_id, institution_id=current_user.institution_id, approved_by=current_user.id)
    if not leave:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Leave request not found")
    return leave

@leave_router.post("/leave-requests/{leave_id}/reject")
def reject_leave_request_endpoint(
    leave_id: int,
    reason: str = Query(..., description="Rejection reason"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Reject a leave request (admin only)"""
    leave = reject_leave_request(db=db, leave_id=leave_id, institution_id=current_user.institution_id, reason=reason)
    if not leave:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Leave request not found")
    return {"message": "Leave request rejected", "id": leave.id}

@leave_router.delete("/leave-requests/{leave_id}")
def delete_leave_request_endpoint(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a leave request (admin only)"""
    delete_leave_request(db=db, leave_id=leave_id, institution_id=current_user.institution_id)
    return {"message": "Leave request deleted"}

class PendingCountResponse(BaseModel):
    pending_leaves: int

@leave_router.get("/leave-requests/pending/count", response_model=PendingCountResponse)
def get_pending_leave_count_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get count of pending leave requests"""
    count = get_pending_leave_count(db=db, institution_id=current_user.institution_id)
    return {"pending_leaves": count}