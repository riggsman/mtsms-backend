"""
Routes for handling file uploads (tenant logo and profile pictures)
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.apis.uploads import (
    upload_tenant_logo,
    upload_profile_picture,
    delete_profile_picture,
    delete_tenant_logo
)
from app.dependencies.tenantDependency import get_db
from app.dependencies.auth import get_current_user_tenant, require_any_role
from app.models.user import User
from app.models.role import UserRole
from app.schemas.tenant_settings import TenantSettingsResponse
from app.schemas.users import UserResponse
import os
from pathlib import Path

upload_router = APIRouter()


@upload_router.post("/uploads/tenant-logo", response_model=TenantSettingsResponse)
async def upload_logo_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Upload tenant logo (admin/super_admin only)
    
    The uploaded file will be prefixed with the tenant domain for easy sorting and fetching.
    The logo URL will be stored in both tenant_settings and tenant tables.
    """
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to upload tenant logo"
        )
    
    # Get global database session for tenant table update
    from app.database.base import get_db_session
    global_db = next(get_db_session())
    
    try:
        settings = await upload_tenant_logo(
            db=db,
            institution_id=current_user.institution_id,
            file=file,
            tenant_db=global_db  # Pass global database for tenant table update
        )
        
        return TenantSettingsResponse.model_validate(settings)
    finally:
        global_db.close()


@upload_router.delete("/uploads/tenant-logo", response_model=TenantSettingsResponse)
def delete_logo_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """
    Delete tenant logo (admin/super_admin only)
    """
    if not current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an institution to delete tenant logo"
        )
    
    settings = delete_tenant_logo(
        db=db,
        institution_id=current_user.institution_id
    )
    
    return TenantSettingsResponse.model_validate(settings)


@upload_router.post("/uploads/profile-picture", response_model=UserResponse)
async def upload_profile_picture_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Upload current user's profile picture
    
    The uploaded file will be prefixed with the tenant domain for easy sorting and fetching.
    Users can upload their own profile picture, or admins can upload for other users.
    """
    user = await upload_profile_picture(
        db=db,
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        file=file
    )
    
    # Convert to response model
    return UserResponse.model_validate(user)


@upload_router.post("/uploads/users/{user_id}/profile-picture", response_model=UserResponse)
async def upload_user_profile_picture_endpoint(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN))
):
    """
    Upload profile picture for a specific user (admin/secretary/super_admin only)
    
    The uploaded file will be prefixed with the tenant domain for easy sorting and fetching.
    """
    # Get the target user to check institution_id
    from app.apis.users import get_user
    target_user = get_user(db=db, user_id=user_id)
    
    # Check if admin is trying to upload for a user from a different institution
    if not current_user.role.startswith('system_'):
        if target_user.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only upload profile pictures for users in your institution"
            )
    
    user = await upload_profile_picture(
        db=db,
        user_id=user_id,
        institution_id=target_user.institution_id,
        file=file
    )
    
    return UserResponse.model_validate(user)


@upload_router.delete("/uploads/profile-picture", response_model=UserResponse)
def delete_profile_picture_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_tenant)
):
    """
    Delete current user's profile picture
    """
    user = delete_profile_picture(
        db=db,
        user_id=current_user.id
    )
    
    return UserResponse.model_validate(user)


@upload_router.delete("/uploads/users/{user_id}/profile-picture", response_model=UserResponse)
def delete_user_profile_picture_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role(UserRole.ADMIN, UserRole.SECRETARY, UserRole.SUPER_ADMIN))
):
    """
    Delete profile picture for a specific user (admin/secretary/super_admin only)
    """
    # Get the target user to check institution_id
    from app.apis.users import get_user
    target_user = get_user(db=db, user_id=user_id)
    
    # Check if admin is trying to delete for a user from a different institution
    if not current_user.role.startswith('system_'):
        if target_user.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete profile pictures for users in your institution"
            )
    
    user = delete_profile_picture(
        db=db,
        user_id=user_id
    )
    
    return UserResponse.model_validate(user)


@upload_router.get("/uploads/{file_path:path}")
async def serve_uploaded_file(
    file_path: str
):
    """
    Serve uploaded files dynamically (logos, profile pictures, etc.)
    
    This endpoint is public and does not require authentication.
    Files are served based on their relative path from the uploads directory.
    The file_path parameter is dynamic and accepts any path structure.
    
    Examples:
    - /api/v1/uploads/logos/tenant_domain_logo_20240101_120000_abc123.jpg
    - /api/v1/uploads/profile_pictures/user_profile.jpg
    - /api/v1/uploads/logos/subfolder/file.png
    """
    # Security: Prevent directory traversal
    # Remove leading slash if present (URLs might have it)
    file_path = file_path.lstrip('/')
    if '..' in file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )
    
    # Construct full file path
    base_upload_dir = os.path.join(os.getcwd(), 'uploads')
    full_path = os.path.join(base_upload_dir, file_path)
    
    # Normalize path to prevent directory traversal
    full_path = os.path.normpath(full_path)
    base_upload_dir = os.path.normpath(base_upload_dir)
    
    # Ensure the file is within the uploads directory
    if not full_path.startswith(base_upload_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if file exists
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        # Try to find the file in the directory (case-insensitive search)
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        
        if os.path.exists(directory) and os.path.isdir(directory):
            # List files in the directory and try case-insensitive match
            try:
                files = os.listdir(directory)
                # Try exact match first
                if filename in files:
                    full_path = os.path.join(directory, filename)
                else:
                    # Try case-insensitive match
                    for f in files:
                        if f.lower() == filename.lower():
                            full_path = os.path.join(directory, f)
                            break
                    else:
                        # File not found even with case-insensitive search
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"File not found: {file_path}"
                        )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {file_path}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
    
    # Determine content type based on file extension
    file_ext = Path(full_path).suffix.lower()
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
    }
    
    content_type = content_types.get(file_ext, 'application/octet-stream')
    
    return FileResponse(
        path=full_path,
        media_type=content_type,
        filename=os.path.basename(full_path)
    )
