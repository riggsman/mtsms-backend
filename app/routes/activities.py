from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.activity import ActivityResponse
from app.apis.activity import get_activities
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

activity = APIRouter()

@activity.get("/activities", response_model=PaginatedResponse[ActivityResponse])
def list_activities(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),  # Allow all authenticated users to view activities
):
    """Get list of activities with pagination"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    # System admins (roles starting with 'system_') can see all activities
    # Tenant users must filter by their institution_id
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view activities")
    
    activities, total = get_activities(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        entity_type=entity_type,
        action=action
    )
    
    return PaginatedResponse.create(
        items=activities,
        total=total,
        page=page,
        page_size=page_size
    )
