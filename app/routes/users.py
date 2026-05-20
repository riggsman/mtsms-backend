from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.schemas.users import UserRequest, UserResponse, UserUpdate, StudentPasswordAssign, ChangePasswordRequest, SuspendUserRequest
from pydantic import BaseModel
from fastapi import HTTPException, status
from app.apis.users import (
    create_user, get_user, get_users, search_users_for_permissions,
    update_user, delete_user, assign_student_password, change_password, suspend_user, suspend_user_by_student_id,
    update_user_permissions
)
from app.dependencies.tenantDependency import get_db, get_db_for_admin
from app.dependencies.auth import get_current_user_tenant, require_any_role, require_any_role_admin
from app.models.user import User
from app.models.role import UserRole
from app.helpers.pagination import PaginatedResponse
from app.helpers.branch_scope import effective_branch_scope_id
from app.helpers.tenant_scope import institution_id_for_user
from app.dependencies.institutionDependency import get_institution_id_from_header
from app.helpers.user_roles import (
    role_string_for_legacy,
    user_can_manage_other_users_passwords,
    user_is_system_admin,
    user_roles_list,
    user_system_permissions_list,
)

user = APIRouter()


class UserSearchResult(BaseModel):
    id: int
    firstname: str
    lastname: str
    email: str
    phone: Optional[str] = None
    username: str
    roles: List[str]
    role: str
    system_permissions: List[str] = []
    is_active: str
    institution_id: Optional[int] = None


class UserPermissionsUpdate(BaseModel):
    permissions: List[str]


class KnownPermissionsResponse(BaseModel):
    known_permissions: List[str]


KNOWN_TENANT_PERMISSION_KEYS = ("manage_billing", "view_analytics", "export_data", "manage_teachers", "manage_students")


@user.get("/users/search", response_model=List[UserSearchResult])
def search_users_endpoint(
    query: str = Query(..., min_length=1, description="Search by name, email, phone, or username"),
    db: Session = Depends(get_db_for_admin),
    current_user: User = Depends(require_any_role_admin(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Search users by name, email, phone, or username for permission management"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    users = search_users_for_permissions(db=db, query=query, institution_id=institution_id)
    results = []
    for u in users:
        results.append(UserSearchResult(
            id=u.id,
            firstname=u.firstname,
            lastname=u.lastname,
            email=u.email,
            phone=u.phone,
            username=u.username,
            roles=user_roles_list(u),
            role=role_string_for_legacy(u),
            system_permissions=user_system_permissions_list(u),
            is_active=u.is_active,
            institution_id=u.institution_id,
        ))
    return results


@user.get("/users/{user_id}/permissions", response_model=UserSearchResult)
def get_user_permissions_endpoint(
    user_id: int,
    db: Session = Depends(get_db_for_admin),
    current_user: User = Depends(require_any_role_admin(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Get user permissions by user ID"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    user = get_user(db=db, user_id=user_id, institution_id=institution_id)
    return UserSearchResult(
        id=user.id,
        firstname=user.firstname,
        lastname=user.lastname,
        email=user.email,
        phone=user.phone,
        username=user.username,
        roles=user_roles_list(user),
        role=role_string_for_legacy(user),
        system_permissions=user_system_permissions_list(user),
        is_active=user.is_active,
        institution_id=user.institution_id,
    )


@user.put("/users/{user_id}/permissions", response_model=UserSearchResult)
def update_user_permissions_endpoint(
    user_id: int,
    perm_update: UserPermissionsUpdate,
    db: Session = Depends(get_db_for_admin),
    current_user: User = Depends(require_any_role_admin(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Update user permissions (add or remove permissions)"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    user = update_user_permissions(db=db, user_id=user_id, permissions=perm_update.permissions, institution_id=institution_id)
    return UserSearchResult(
        id=user.id,
        firstname=user.firstname,
        lastname=user.lastname,
        email=user.email,
        phone=user.phone,
        username=user.username,
        roles=user_roles_list(user),
        role=role_string_for_legacy(user),
        system_permissions=user_system_permissions_list(user),
        is_active=user.is_active,
        institution_id=user.institution_id,
    )


@user.get("/users/known-permissions", response_model=KnownPermissionsResponse)
def get_known_permissions_endpoint(
    current_user: User = Depends(require_any_role_admin(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
):
    """Get list of known permission keys that can be assigned"""
    return KnownPermissionsResponse(known_permissions=list(KNOWN_TENANT_PERMISSION_KEYS))

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
    current_user: User = Depends(get_current_user_tenant),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Get a user by ID"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    return get_user(db=db, user_id=user_id, institution_id=institution_id)

@user.get("/users", response_model=PaginatedResponse[UserResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
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
        is_system_admin = user_is_system_admin(current_user)
        if not is_system_admin:
            institution_id = current_user.institution_id
            if not institution_id:
                from app.exceptions import ValidationError
                raise ValidationError("User must belong to an institution to view users")
    
    branch_scope = effective_branch_scope_id(db, current_user)

    users, total = get_users(
        db=db,
        skip=skip,
        limit=page_size,
        role=role,
        exclude_role=exclude_role,
        institution_id=institution_id,
        branch_id=branch_scope,
    )
    
    # Fix invalid datetime values (MySQL zero dates) before Pydantic serialization
    from datetime import datetime
    fixed_users = []
    for user_obj in users:
        # Create a dict with all user attributes, fixing invalid datetimes
        user_dict = {
            'id': user_obj.id,
            'institution_id': user_obj.institution_id,
            'department_id': getattr(user_obj, 'department_id', None),
            'position': getattr(user_obj, 'position', None),
            'designation': getattr(user_obj, 'position', None),
            'title': getattr(user_obj, 'position', None),
            'firstname': user_obj.firstname,
            'middlename': user_obj.middlename,
            'lastname': user_obj.lastname,
            'gender': user_obj.gender,
            'address': user_obj.address,
            'email': user_obj.email,
            'phone': user_obj.phone,
            'username': user_obj.username,
            'roles': user_roles_list(user_obj),
            'role': role_string_for_legacy(user_obj),
            'user_type': getattr(user_obj, 'user_type', 'TENANT'),
            'is_active': user_obj.is_active,
            'must_change_password': getattr(user_obj, 'must_change_password', 'false'),
            'profile_picture': getattr(user_obj, 'profile_picture', None),
            'language': getattr(user_obj, 'language', 'en') or 'en',
            'branch_id': getattr(user_obj, 'branch_id', None),
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
    page_size: int = Query(10, ge=1, le=1000),
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
            'department_id': getattr(user, 'department_id', None),
            'position': getattr(user, 'position', None),
            'designation': getattr(user, 'position', None),
            'title': getattr(user, 'position', None),
            'firstname': user.firstname,
            'middlename': user.middlename,
            'lastname': user.lastname,
            'gender': user.gender,
            'address': user.address,
            'email': user.email,
            'phone': user.phone,
            'username': user.username,
            'roles': user_roles_list(user),
            'role': role_string_for_legacy(user),
            'user_type': user.user_type,
            'is_active': user.is_active,
            'must_change_password': user.must_change_password,
            'profile_picture': getattr(user, 'profile_picture', None),
            'language': getattr(user, 'language', 'en') or 'en',
            'branch_id': getattr(user, 'branch_id', None),
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
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Update a user"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    return update_user(db=db, user_id=user_id, user_update=user_update, current_user=current_user, institution_id=institution_id)

@user.delete("/users/{user_id}", status_code=204)
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)),
    header_institution_id: Optional[int] = Depends(get_institution_id_from_header),
):
    """Delete a user (soft delete)"""
    institution_id = institution_id_for_user(current_user, header_institution_id=header_institution_id)
    delete_user(db=db, user_id=user_id, current_user=current_user, institution_id=institution_id)
    return None

@user.post("/students/assign-password", response_model=UserResponse, status_code=201)
def assign_student_password_endpoint(
    password_data: StudentPasswordAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.STAFF, UserRole.SECRETARY))
):
    """Assign password to a student (creates or updates user account)"""
    return assign_student_password(
        db=db,
        student_id=password_data.student_id,
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
    is_admin = user_can_manage_other_users_passwords(current_user)
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

@user.post("/users/{user_id}/suspend", response_model=UserResponse)
def suspend_user_endpoint(
    user_id: int,
    suspend_data: SuspendUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Suspend a user account"""
    return suspend_user(
        db=db,
        user_id=user_id,
        reason=suspend_data.reason,
        current_user=current_user
    )

@user.post("/students/{student_id}/suspend", response_model=UserResponse)
def suspend_student_endpoint(
    student_id: int,
    suspend_data: SuspendUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """Suspend a student account (by student_id)"""
    return suspend_user_by_student_id(
        db=db,
        student_id=student_id,
        reason=suspend_data.reason,
        current_user=current_user
    )

class UserMeSettingsResponse(BaseModel):
    language: str = "en"
    theme: Optional[str] = None


class UserMeSettingsUpdate(BaseModel):
    language: Optional[str] = None
    theme: Optional[str] = None


@user.get("/users/me/settings", response_model=UserMeSettingsResponse)
def get_my_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    """Current user's UI preferences (language persisted; theme echoed client-side only)."""
    return UserMeSettingsResponse(
        language=getattr(current_user, "language", "en") or "en",
        theme=None,
    )


@user.put("/users/me/settings", response_model=UserMeSettingsResponse)
def update_my_settings(
    payload: UserMeSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant),
):
    """Update language and/or receive echoed theme for client cache (theme not stored server-side)."""
    if payload.language is not None:
        lang = payload.language.lower().strip()
        if lang not in {"en", "fr"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported language. Supported languages: en, fr",
            )
        current_user.language = lang
        db.add(current_user)
        db.commit()
        db.refresh(current_user)

    if payload.theme is not None and payload.theme not in {"light", "dark"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid theme. Supported values: light, dark",
        )

    return UserMeSettingsResponse(
        language=getattr(current_user, "language", "en") or "en",
        theme=payload.theme,
    )


class UpdateLanguageRequest(BaseModel):
    language: str

@user.patch("/users/me/language", response_model=UserResponse)
def update_my_language(
    payload: UpdateLanguageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """Update current user's preferred language"""
    lang = payload.language.lower().strip()
    
    # Validate language (only allow 'en' and 'fr' for now)
    if lang not in {"en", "fr"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported language. Supported languages: en, fr"
        )
    
    # Update user's language
    current_user.language = lang
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    # Return updated user
    from datetime import datetime
    user_dict = {
        'id': current_user.id,
        'institution_id': current_user.institution_id,
        'department_id': getattr(current_user, 'department_id', None),
        'position': getattr(current_user, 'position', None),
        'designation': getattr(current_user, 'position', None),
        'title': getattr(current_user, 'position', None),
        'firstname': current_user.firstname,
        'middlename': current_user.middlename,
        'lastname': current_user.lastname,
        'gender': current_user.gender,
        'address': current_user.address,
        'email': current_user.email,
        'phone': current_user.phone,
        'username': current_user.username,
        'roles': user_roles_list(current_user),
        'role': role_string_for_legacy(current_user),
        'user_type': getattr(current_user, 'user_type', 'TENANT'),
        'is_active': current_user.is_active,
        'must_change_password': getattr(current_user, 'must_change_password', 'false'),
        'profile_picture': getattr(current_user, 'profile_picture', None),
        'language': getattr(current_user, 'language', 'en') or 'en',
        'created_at': None if (current_user.created_at is None or 
                               (isinstance(current_user.created_at, datetime) and current_user.created_at.year == 0)) 
                        else current_user.created_at,
        'updated_at': None if (current_user.updated_at is None or 
                               (isinstance(current_user.updated_at, datetime) and current_user.updated_at.year == 0)) 
                        else current_user.updated_at,
    }
    return UserResponse(**user_dict)
