from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.schemas.utility_request import UtilityRequestCreate, UtilityRequestUpdate, UtilityRequestResponse
from app.apis.utility_request import (
    create_utility_request, get_utility_requests, get_utility_request_by_id,
    update_utility_request, approve_utility_request, reject_utility_request, 
    complete_utility_request, delete_utility_request, get_pending_utility_count
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

utility_router = APIRouter()

@utility_router.post("/utility-requests", response_model=UtilityRequestResponse, status_code=201)
def create_utility_request_endpoint(
    util_data: UtilityRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Create a new utility request"""
    return create_utility_request(db=db, util_data=util_data, institution_id=current_user.institution_id, user_id=current_user.id)

@utility_router.get("/utility-requests", response_model=PaginatedResponse)
def get_utility_requests_endpoint(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get all utility requests for the institution"""
    return get_utility_requests(db=db, institution_id=current_user.institution_id, status=status, page=page, page_size=page_size)

@utility_router.get("/utility-requests/{util_id}", response_model=UtilityRequestResponse)
def get_utility_request_endpoint(
    util_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a specific utility request"""
    utility = get_utility_request_by_id(db=db, util_id=util_id, institution_id=current_user.institution_id)
    if not utility:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Utility request not found")
    return utility

@utility_router.put("/utility-requests/{util_id}", response_model=UtilityRequestResponse)
def update_utility_request_endpoint(
    util_id: int,
    util_data: UtilityRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update a utility request (admin only)"""
    utility = update_utility_request(db=db, util_id=util_id, util_data=util_data, institution_id=current_user.institution_id)
    if not utility:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Utility request not found")
    return utility

@utility_router.post("/utility-requests/{util_id}/approve", response_model=UtilityRequestResponse)
def approve_utility_request_endpoint(
    util_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Approve a utility request (admin only)"""
    utility = approve_utility_request(db=db, util_id=util_id, institution_id=current_user.institution_id, handled_by=current_user.id)
    if not utility:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Utility request not found")
    return utility

@utility_router.post("/utility-requests/{util_id}/reject")
def reject_utility_request_endpoint(
    util_id: int,
    notes: Optional[str] = Query(None, description="Rejection notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Reject a utility request (admin only)"""
    utility = reject_utility_request(db=db, util_id=util_id, institution_id=current_user.institution_id, notes=notes or "")
    if not utility:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Utility request not found")
    return {"message": "Utility request rejected", "id": utility.id}

@utility_router.post("/utility-requests/{util_id}/complete", response_model=UtilityRequestResponse)
def complete_utility_request_endpoint(
    util_id: int,
    notes: Optional[str] = Query(None, description="Completion notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Mark utility request as completed (admin only)"""
    utility = complete_utility_request(db=db, util_id=util_id, institution_id=current_user.institution_id, notes=notes or "")
    if not utility:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Utility request not found")
    return utility

@utility_router.delete("/utility-requests/{util_id}")
def delete_utility_request_endpoint(
    util_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a utility request (admin only)"""
    delete_utility_request(db=db, util_id=util_id, institution_id=current_user.institution_id)
    return {"message": "Utility request deleted"}

class PendingCountResponse(BaseModel):
    pending_utilities: int

@utility_router.get("/utility-requests/pending/count", response_model=PendingCountResponse)
def get_pending_utility_count_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get count of pending utility requests"""
    count = get_pending_utility_count(db=db, institution_id=current_user.institution_id)
    return {"pending_utilities": count}