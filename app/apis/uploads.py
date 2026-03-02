"""
API functions for handling file uploads (tenant logo and profile pictures)
"""
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from typing import Optional
from app.models.user import User
from app.models.tenant_settings import TenantSettings
from app.models.tenant import Tenant
from app.helpers.file_upload import save_uploaded_file, delete_file
from app.database.base import get_db_session
from app.exceptions import NotFoundError


def get_tenant_domain(institution_id: int) -> str:
    """
    Get tenant domain from institution_id
    
    Args:
        institution_id: Institution/Tenant ID
        
    Returns:
        Tenant domain string, or 'default' if not found
    """
    if not institution_id:
        return "default"
    
    global_db = next(get_db_session())
    try:
        tenant = global_db.query(Tenant).filter(Tenant.id == institution_id).first()
        if tenant and tenant.domain:
            return tenant.domain
        return "default"
    except Exception as e:
        print(f"Error fetching tenant domain: {e}")
        return "default"
    finally:
        global_db.close()


async def upload_tenant_logo(
    db: Session,
    institution_id: int,
    file: UploadFile,
    tenant_db: Optional[Session] = None
) -> TenantSettings:
    """
    Upload tenant logo and update both tenant_settings and tenant table
    
    Args:
        db: Database session for tenant_settings (shared or tenant-specific)
        institution_id: Institution ID
        file: Uploaded file
        tenant_db: Optional database session for tenant table (global database)
        
    Returns:
        Updated TenantSettings object
        
    Raises:
        NotFoundError if tenant settings don't exist
        HTTPException if upload fails
    """
    from app.database.base import get_db_session
    from app.models.tenant import Tenant
    from app.helpers.file_upload import get_file_url
    
    # Get tenant domain for file prefixing
    tenant_domain = get_tenant_domain(institution_id)
    
    # Get or create tenant settings
    settings = db.query(TenantSettings).filter(
        TenantSettings.institution_id == institution_id
    ).first()
    
    if not settings:
        # Create new settings if they don't exist
        settings = TenantSettings(institution_id=institution_id)
        db.add(settings)
        db.flush()
    
    # Delete old logo if it exists
    old_logo_path = settings.logo
    if old_logo_path:
        try:
            delete_file(old_logo_path)
        except Exception as e:
            print(f"Warning: Could not delete old logo: {e}")
    # Save new logo file
    try:
        file_path, relative_path = await save_uploaded_file(
            file=file,
            tenant_domain=tenant_domain,
            file_category='logo'
        )
        
        # Generate logo URL
        logo_url = get_file_url(relative_path, base_url="/api/v1/uploads")
        
        # Update settings with new logo path
        settings.logo = relative_path
        db.commit()
        db.refresh(settings)
        
        # Update tenant table with logo_url
        # Use provided tenant_db or get global database session
        if tenant_db is None:
            tenant_db = next(get_db_session())
            should_close_tenant_db = True
        else:
            should_close_tenant_db = False
        
        try:
            tenant = tenant_db.query(Tenant).filter(Tenant.id == institution_id).first()
            if tenant:
                # Delete old logo file if tenant had a different logo_url
                if tenant.logo_url and tenant.logo_url != logo_url:
                    try:
                        # Extract relative path from old URL
                        old_relative = tenant.logo_url.replace("/api/v1/uploads/", "")
                        if old_relative and old_relative != relative_path:
                            delete_file(old_relative)
                    except Exception as e:
                        print(f"Warning: Could not delete old tenant logo: {e}")
                
                tenant.logo_url = logo_url
                tenant_db.commit()
                tenant_db.refresh(tenant)
        except Exception as e:
            # Log error but don't fail - settings are already updated
            from app.helpers.logger import logger
            logger.error(f"Error updating tenant logo_url: {e}")
        finally:
            if should_close_tenant_db:
                tenant_db.close()
        
        return settings
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload logo: {str(e)}"
        )


async def upload_profile_picture(
    db: Session,
    user_id: int,
    institution_id: Optional[int],
    file: UploadFile
) -> User:
    """
    Upload user profile picture
    
    Args:
        db: Database session
        user_id: User ID
        institution_id: Institution ID (for tenant domain)
        file: Uploaded file
        
    Returns:
        Updated User object
        
    Raises:
        NotFoundError if user doesn't exist
        HTTPException if upload fails
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    
    # Get tenant domain for file prefixing
    tenant_domain = get_tenant_domain(institution_id or user.institution_id)
    
    # Delete old profile picture if it exists
    if user.profile_picture:
        try:
            delete_file(user.profile_picture)
        except Exception as e:
            print(f"Warning: Could not delete old profile picture: {e}")
    
    # Save new profile picture file
    try:
        file_path, relative_path = await save_uploaded_file(
            file=file,
            tenant_domain=tenant_domain,
            file_category='profile_picture'
        )
        
        # Update user with new profile picture path
        user.profile_picture = relative_path
        db.commit()
        db.refresh(user)
        
        return user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile picture: {str(e)}"
        )


def delete_profile_picture(
    db: Session,
    user_id: int
) -> User:
    """
    Delete user profile picture
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Updated User object
        
    Raises:
        NotFoundError if user doesn't exist
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found")
    
    # Delete file if it exists
    if user.profile_picture:
        try:
            delete_file(user.profile_picture)
        except Exception as e:
            print(f"Warning: Could not delete profile picture file: {e}")
    
    # Clear profile picture path
    user.profile_picture = None
    db.commit()
    db.refresh(user)
    
    return user


def delete_tenant_logo(
    db: Session,
    institution_id: int
) -> TenantSettings:
    """
    Delete tenant logo
    
    Args:
        db: Database session
        institution_id: Institution ID
        
    Returns:
        Updated TenantSettings object
        
    Raises:
        NotFoundError if tenant settings don't exist
    """
    settings = db.query(TenantSettings).filter(
        TenantSettings.institution_id == institution_id
    ).first()
    
    if not settings:
        raise NotFoundError(f"Tenant settings for institution {institution_id} not found")
    
    # Delete file if it exists
    if settings.logo:
        try:
            delete_file(settings.logo)
        except Exception as e:
            print(f"Warning: Could not delete logo file: {e}")
    
    # Clear logo path
    settings.logo = None
    db.commit()
    db.refresh(settings)
    
    return settings
