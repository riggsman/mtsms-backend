from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.classes import ClassRequest, ClassResponse, ClassUpdate
from app.apis.classes import (
    create_class, get_class, get_classes,
    update_class, delete_class
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

class_router = APIRouter()

@class_router.post("/classes", response_model=ClassResponse, status_code=201)
def create_class_endpoint(
    class_data: ClassRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Create a new class"""
    institution_id = class_data.institution_id or current_user.institution_id
    
    if not institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or ensure the user belongs to an institution")
    
    return create_class(db=db, class_data=class_data, institution_id=institution_id, current_user=current_user)

@class_router.get("/classes/{class_id}", response_model=ClassResponse)
def get_class_endpoint(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a class by ID"""
    return get_class(db=db, class_id=class_id)

@class_router.get("/classes", response_model=PaginatedResponse[ClassResponse])
def list_classes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    institution_level: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get list of classes with pagination"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view classes")
    
    classes, total = get_classes(
        db=db,
        skip=skip,
        limit=page_size,
        institution_id=institution_id,
        institution_level=institution_level,
        department_id=department_id
    )
    return PaginatedResponse.create(
        items=classes,
        total=total,
        page=page,
        page_size=page_size
    )

@class_router.put("/classes/{class_id}", response_model=ClassResponse)
def update_class_endpoint(
    class_id: int,
    class_update: ClassUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Update a class"""
    return update_class(db=db, class_id=class_id, class_update=class_update, current_user=current_user)

@class_router.delete("/classes/{class_id}", status_code=204)
def delete_class_endpoint(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a class (soft delete)"""
    delete_class(db=db, class_id=class_id, current_user=current_user)
    return None
