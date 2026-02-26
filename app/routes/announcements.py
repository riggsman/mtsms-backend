from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse
from app.apis.announcements import (
    create_announcement,
    get_announcement,
    get_announcements,
    update_announcement,
    delete_announcement
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

announcement_router = APIRouter()

@announcement_router.get("/announcements", response_model=PaginatedResponse[AnnouncementResponse])
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of announcements for the current tenant (any authenticated tenant user)"""
    if not current_user.institution_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to view announcements"
        )
    
    skip = (page - 1) * page_size
    # Get user role for filtering
    user_role = current_user.role if current_user.role else None
    # Normalize role names (remove "system_" prefix if present)
    if user_role and user_role.startswith("system_"):
        user_role = user_role.replace("system_", "")
    
    announcements, total = get_announcements(
        db=db,
        institution_id=current_user.institution_id,
        skip=skip,
        limit=page_size,
        user_role=user_role
    )
    return PaginatedResponse.create(
        items=announcements,
        total=total,
        page=page,
        page_size=page_size
    )

@announcement_router.get("/announcements/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement_endpoint(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get an announcement by ID (tenant-scoped)"""
    if not current_user.institution_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to view announcements"
        )
    
    return get_announcement(db=db, announcement_id=announcement_id, institution_id=current_user.institution_id)

@announcement_router.post("/announcements", response_model=AnnouncementResponse, status_code=201)
def create_announcement_endpoint(
    announcement_data: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Create a new announcement (admin/secretary only)"""
    if not current_user.institution_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to create announcements"
        )
    
    return create_announcement(
        db=db,
        announcement=announcement_data,
        institution_id=current_user.institution_id,
        current_user=current_user
    )

@announcement_router.put("/announcements/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement_endpoint(
    announcement_id: int,
    announcement_update: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Update an announcement (admin/secretary only)"""
    if not current_user.institution_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to update announcements"
        )
    
    return update_announcement(
        db=db,
        announcement_id=announcement_id,
        announcement_update=announcement_update,
        institution_id=current_user.institution_id,
        current_user=current_user
    )

@announcement_router.delete("/announcements/{announcement_id}", status_code=204)
def delete_announcement_endpoint(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SECRETARY))
):
    """Delete an announcement (admin/secretary only)"""
    if not current_user.institution_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to delete announcements"
        )
    
    delete_announcement(
        db=db,
        announcement_id=announcement_id,
        institution_id=current_user.institution_id,
        current_user=current_user
    )
    return None
