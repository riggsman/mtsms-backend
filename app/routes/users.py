from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.schemas.users import UserRequest, UserResponse, UserUpdate, StudentPasswordAssign, ChangePasswordRequest
from app.apis.users import (
    create_user, get_user, get_users,
    update_user, delete_user, assign_student_password, change_password
)
from app.dependencies.tenantDependency import get_db, get_db_for_admin
from app.dependencies.auth import get_current_user_tenant, require_any_role, require_any_role_admin
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse

user = APIRouter()

@user.post("/users", response_model=UserResponse, status_code=201)
def create_user_endpoint(
    user_data: UserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN))
):
    """Create a new user"""
    return create_user(db=db, user=user_data, creator_user=current_user)

@user.get("/users/{user_id}", response_model=UserResponse)
def get_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Get a user by ID"""
    return get_user(db=db, user_id=user_id)

@user.get("/users", response_model=PaginatedResponse[UserResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role: Optional[str] = Query(None),
    exclude_role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
):
    """Get list of users with pagination"""
    skip = (page - 1) * page_size
    
    # Determine institution_id for filtering
    # System admins (roles starting with 'system_') can see all users
    # Tenant users must filter by their institution_id
    institution_id = None
    if current_user:
        is_system_admin = current_user.role and current_user.role.startswith('system_')
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view users")
    
    users, total = get_users(
        db=db,
        skip=skip,
        limit=page_size,
        role=role,
        exclude_role=exclude_role,
        institution_id=institution_id
    )
    
    # Fix invalid datetime values (MySQL zero dates) before Pydantic serialization
    from datetime import datetime
    fixed_users = []
    for user_obj in users:
        # Create a dict with all user attributes, fixing invalid datetimes
        user_dict = {
            'id': user_obj.id,
            'institution_id': user_obj.institution_id,
            'firstname': user_obj.firstname,
            'middlename': user_obj.middlename,
            'lastname': user_obj.lastname,
            'gender': user_obj.gender,
            'address': user_obj.address,
            'email': user_obj.email,
            'phone': user_obj.phone,
            'username': user_obj.username,
            'role': user_obj.role,
            'user_type': getattr(user_obj, 'user_type', 'TENANT'),
            'is_active': user_obj.is_active,
            'must_change_password': getattr(user_obj, 'must_change_password', 'false'),
            'created_at': None if (user_obj.created_at is None or 
                                   (isinstance(user_obj.created_at, datetime) and user_obj.created_at.year == 0)) 
                            else user_obj.created_at,
            'updated_at': None if (user_obj.updated_at is None or 
                                   (isinstance(user_obj.updated_at, datetime) and user_obj.updated_at.year == 0)) 
                            else user_obj.updated_at,
        }
        # Create UserResponse from the fixed dict
        fixed_users.append(UserResponse(**user_dict))
    
    return PaginatedResponse.create(
        items=fixed_users,
        total=total,
        page=page,
        page_size=page_size
    )

@user.get("/admin/users", response_model=PaginatedResponse[UserResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db_for_admin),
    current_user: User = Depends(require_any_role_admin(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
):
    """Get list of users with pagination (admin route - uses global database, no tenant header required)"""
    skip = (page - 1) * page_size
    users, total = get_users(
        db=db,
        skip=skip,
        limit=page_size,
        role=role
    )
    
    # Fix invalid datetime values (MySQL zero dates)
    from datetime import datetime
    fixed_users = []
    for user in users:
        # Create a copy of user attributes
        user_dict = {
            'id': user.id,
            'institution_id': user.institution_id,
            'firstname': user.firstname,
            'middlename': user.middlename,
            'lastname': user.lastname,
            'gender': user.gender,
            'address': user.address,
            'email': user.email,
            'phone': user.phone,
            'username': user.username,
            'role': user.role,
            'user_type': user.user_type,
            'is_active': user.is_active,
            'must_change_password': user.must_change_password,
            'created_at': None if (user.created_at is None or 
                                   (isinstance(user.created_at, datetime) and user.created_at.year == 0)) 
                            else user.created_at,
            'updated_at': None if (user.updated_at is None or 
                                   (isinstance(user.updated_at, datetime) and user.updated_at.year == 0)) 
                            else user.updated_at,
        }
        fixed_users.append(UserResponse(**user_dict))
    
    return PaginatedResponse.create(
        items=fixed_users,
        total=total,
        page=page,
        page_size=page_size
    )

@user.put("/users/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN))
):
    """Update a user"""
    return update_user(db=db, user_id=user_id, user_update=user_update, current_user=current_user)

@user.delete("/users/{user_id}", status_code=204)
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Delete a user (soft delete)"""
    delete_user(db=db, user_id=user_id, current_user=current_user)
    return None

@user.post("/students/{student_id}/assign-password", response_model=UserResponse, status_code=201)
def assign_student_password_endpoint(
    student_id: int,
    password_data: StudentPasswordAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.STAFF, UserRole.SECRETARY))
):
    """Assign password to a student (creates or updates user account)"""
    return assign_student_password(
        db=db,
        student_id=student_id,
        password=password_data.password,
        username=password_data.username,
        institution_id=current_user.institution_id
    )

@user.post("/users/{user_id}/change-password", response_model=UserResponse)
def change_password_endpoint(
    user_id: int,
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Change user password (for first-time login or regular password change)"""
    # Users can only change their own password unless they're admin or system admin
    is_admin = (current_user.role == UserRole.ADMIN.value or 
                current_user.role == UserRole.SUPER_ADMIN.value or
                (current_user.role and current_user.role.startswith('system_')))
    if not is_admin:
        if current_user.id != user_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only change your own password"
            )
    
    return change_password(
        db=db,
        user_id=user_id,
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        current_user=current_user  # Pass current_user for activity logging
    )
