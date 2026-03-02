from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import UploadFile
from app.database.sessionManager import create_tenant_database, get_tenant_db, get_shared_db, get_database_mode
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantRequest, TenantResponse, TenantUpdate
from app.helpers.pagination import paginate_query
from app.exceptions import NotFoundError, ConflictError, ValidationError
from app.authentication.authenticator import hash_password
from app.services.email_service import EmailService
from app.helpers.async_helper import run_async_safe

async def create_new_tenant(db: Session, tenant: TenantRequest, logo_file: Optional[UploadFile] = None):
    """Create a new tenant"""
    # Check if tenant already exists
    existing = get_tenant_by_name(db, tenant.name)
    if existing:
        raise ConflictError(f"Tenant with name '{tenant.name}' already exists")
    
    # Check if domain already exists
    if tenant.domain:
        from app.models.tenant import Tenant
        existing_domain = db.query(Tenant).filter(Tenant.domain == tenant.domain).first()
        if existing_domain:
            raise ConflictError(f"Tenant with domain '{tenant.domain}' already exists")
    
    # Check database mode - only create database if in multi-tenant mode
    from app.database.sessionManager import get_database_mode
    mode = get_database_mode()
    
    tenant_database_url = None
    if mode == 'multi_tenant':
        # Generate database URL only in multi-tenant mode
        database_name = tenant.database_name or tenant.name
        tenant_database_url = await create_tenant_database(database_name, user="root", password="")
    # In shared mode, database_url can be None
    
    new_tenant = Tenant(
        name=tenant.name,
        category=tenant.category.upper(),  # Ensure uppercase (HI or SI)
        domain=tenant.domain,
        database_url=tenant_database_url,
        is_active=tenant.is_active if tenant.is_active is not None else True
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    
    # Store tenant ID for user creation
    tenant_id = new_tenant.id
    
    # Create admin user if credentials provided
    if tenant.admin_username and tenant.admin_password:
        # Determine which database to use for the user
        user_mode = get_database_mode()
        if user_mode == 'shared':
            # In shared mode, use the shared database session
            user_db = get_shared_db()()
            should_close = False
        else:
            # In multi-tenant mode, use tenant-specific database
            TenantSessionLocal = get_tenant_db(tenant.name)
            user_db = TenantSessionLocal()
            should_close = True
        
        try:
            # Check if username already exists for this tenant
            existing_user = user_db.query(User).filter(
                User.username == tenant.admin_username,
                User.institution_id == tenant_id
            ).first()
            
            if existing_user:
                # If user exists, update password and must_change_password
                existing_user.password = hash_password(tenant.admin_password)
                existing_user.must_change_password = 'true' if tenant.must_change_password else 'false'
                existing_user.institution_id = tenant_id  # Ensure it's set correctly
                existing_user.role = 'super_admin'
                existing_user.user_type = 'TENANT'
                user_db.commit()
                user_db.refresh(existing_user)
            else:
                # Create new admin user with tenant ID
                admin_user = User(
                    institution_id=tenant_id,  # Set to the tenant's ID
                    firstname='Admin',
                    middlename='',
                    lastname=tenant.name,
                    gender='Other',
                    address='',
                    email=f'{tenant.admin_username}@{tenant.domain or tenant.name}',
                    phone='',
                    username=tenant.admin_username,
                    password=hash_password(tenant.admin_password),
                    role='super_admin',
                    user_type='TENANT',
                    is_active='active',
                    must_change_password='true' if tenant.must_change_password else 'false'
                )
                user_db.add(admin_user)
                user_db.commit()
                user_db.refresh(admin_user)
                
                # Verify the user was created with correct institution_id
                if admin_user.institution_id != tenant_id:
                    raise Exception(f"Failed to set institution_id correctly. Expected {tenant_id}, got {admin_user.institution_id}")
                
                # Send registration email asynchronously (non-blocking)
                admin_email = admin_user.email
                if admin_email:
                    run_async_safe(
                        EmailService.send_tenant_registration_email(
                            tenant_name=tenant.name,
                            admin_email=admin_email,
                            admin_username=tenant.admin_username,
                            admin_password=tenant.admin_password,  # Send plain password for first login
                            domain=tenant.domain
                        )
                    )
        except Exception as e:
            # Log error but don't fail tenant creation
            from app.helpers.logger import logger
            logger.error(f"Error creating admin user for tenant {tenant.name}: {e}")
            # Re-raise if it's a critical error
            if "institution_id" in str(e):
                raise
        finally:
            if should_close:
                user_db.close()
    
    # Create tenant_settings entry if it doesn't exist (for logo storage)
    from app.models.tenant_settings import TenantSettings
    mode = get_database_mode()
    if mode == 'shared':
        settings_db = get_shared_db()()
        should_close_settings = False
    else:
        TenantSessionLocal = get_tenant_db(tenant.name)
        settings_db = TenantSessionLocal()
        should_close_settings = True
    
    try:
        # Check if tenant_settings already exists
        existing_settings = settings_db.query(TenantSettings).filter(
            TenantSettings.institution_id == tenant_id
        ).first()
        
        if not existing_settings:
            # Create new tenant_settings entry
            new_settings = TenantSettings(institution_id=tenant_id)
            settings_db.add(new_settings)
            settings_db.commit()
            settings_db.refresh(new_settings)
    except Exception as e:
        from app.helpers.logger import logger
        logger.warning(f"Could not create tenant_settings for tenant {tenant.name}: {e}")
    finally:
        if should_close_settings:
            settings_db.close()
    
    # Handle logo upload if provided during creation
    if logo_file:
        await _upload_tenant_logo_safe(
            tenant=new_tenant,
            tenant_id=tenant_id,
            logo_file=logo_file,
            global_db=db  # Pass global database session
        )
    
    # Enrich tenant with admin_username and logo_url before returning
    new_tenant = _enrich_tenant(db, new_tenant)
    return new_tenant

def get_tenant_by_name(db: Session, name: str) -> Optional[Tenant]:
    """Get tenant by name"""
    tenant = db.query(Tenant).filter(Tenant.name == name).first()
    if tenant:
        # Enrich tenant with admin_username and logo_url
        tenant = _enrich_tenant(db, tenant)
    return tenant

def get_tenant_by_id(db: Session, tenant_id: int) -> Tenant:
    """Get tenant by ID"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")
    # Enrich tenant with admin_username and logo_url
    tenant = _enrich_tenant(db, tenant)
    return tenant

def _add_admin_username(db: Session, tenant: Tenant) -> Tenant:
    """Helper function to add admin username to tenant object"""
    try:
        # Get admin user for this tenant
        # Check if we're in shared mode or need tenant-specific DB
        mode = get_database_mode()
        if mode == 'shared':
            # Use the same db session
            admin_user = db.query(User).filter(
                User.institution_id == tenant.id,
                User.role == 'super_admin'
            ).first()
        else:
            # Need to query tenant-specific database
            try:
                TenantSessionLocal = get_tenant_db(tenant.name)
                tenant_db = TenantSessionLocal()
                try:
                    admin_user = tenant_db.query(User).filter(
                        User.institution_id == tenant.id,
                        User.role == 'super_admin'
                    ).first()
                finally:
                    tenant_db.close()
            except Exception:
                admin_user = None
        
        if admin_user:
            # Add admin_username as a dynamic attribute
            setattr(tenant, 'admin_username', admin_user.username)
        else:
            setattr(tenant, 'admin_username', None)
    except Exception:
        setattr(tenant, 'admin_username', None)
    return tenant


def _add_logo_url(db: Session, tenant: Tenant) -> Tenant:
    """Helper function to add logo URL to tenant object"""
    try:
        # First check if tenant has logo_url directly in the tenant table
        if tenant.logo_url:
            # Logo URL is already stored in tenant table, use it
            return tenant
        
        # Fallback: Check tenant_settings if logo_url not in tenant table
        from app.models.tenant_settings import TenantSettings
        from app.models.tenant import Tenant
        from app.helpers.file_upload import get_file_url
        
        # Determine which database to use for tenant_settings
        mode = get_database_mode()
        if mode == 'shared':
            # In shared mode, use the same db session (shared database)
            tenant_settings = db.query(TenantSettings).filter(
                TenantSettings.institution_id == tenant.id
            ).first()
        else:
            # In multi-tenant mode, need to query tenant-specific database
            try:
                TenantSessionLocal = get_tenant_db(tenant.name)
                tenant_db = TenantSessionLocal()
                try:
                    tenant_settings = tenant_db.query(TenantSettings).filter(
                        TenantSettings.institution_id == tenant.id
                    ).first()
                finally:
                    tenant_db.close()
            except Exception:
                tenant_settings = None
        
        if tenant_settings and tenant_settings.logo:
            # Generate URL for the logo file
            logo_url = get_file_url(tenant_settings.logo, base_url="/api/v1/uploads")
            # Update tenant table with logo_url for future use
            try:
                tenant.logo_url = logo_url
                db.commit()
                db.refresh(tenant)
            except Exception as e:
                # If update fails, just set the attribute for this response
                from app.helpers.logger import logger
                logger.warning(f"Could not update tenant logo_url in database: {e}")
                setattr(tenant, 'logo_url', logo_url)
        else:
            setattr(tenant, 'logo_url', None)
    except Exception as e:
        # Log error but don't fail
        from app.helpers.logger import logger
        logger.error(f"Error fetching logo for tenant {tenant.id}: {e}")
        setattr(tenant, 'logo_url', None)
    return tenant


def _enrich_tenant(db: Session, tenant: Tenant) -> Tenant:
    """Helper function to enrich tenant with admin_username and logo_url"""
    print("OK LET US PROCEED..... Enrich tenant with admin_username and logo_url.")
    tenant = _add_admin_username(db, tenant)
    tenant = _add_logo_url(db, tenant)
    print("OK LET US PROCEED..... Enrichment complete. ", tenant.logo_url)
    return tenant

def get_all_tenants(
    db: Session,
    skip: int = 0,
    limit: int = 10
) -> tuple[List[Tenant], int]:
    """Get all tenants with pagination"""
    query = db.query(Tenant)
    tenants, total = paginate_query(query, page=(skip // limit) + 1, page_size=limit)
    # Enrich each tenant with admin_username and logo_url
    tenants = [_enrich_tenant(db, tenant) for tenant in tenants]
    return tenants, total

async def update_tenant(
    db: Session, 
    tenant_id: int, 
    tenant_update: TenantUpdate,
    logo_file: Optional[UploadFile] = None
) -> Tenant:
    """
    Update a tenant and optionally update admin user and logo.
    
    Args:
        db: Database session (global/shared database)
        tenant_id: ID of the tenant to update
        tenant_update: TenantUpdate object with fields to update
        logo_file: Optional logo file to upload
        
    Returns:
        Updated Tenant object with enriched data (admin_username, logo_url)
    """
    print("OK LET US PROCEED.... Update tenant function called.")
    # Get tenant directly without enrichment to avoid redundant queries
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")
    
    # Extract admin user fields before processing tenant update
    admin_username = tenant_update.admin_username
    admin_password = tenant_update.admin_password
    must_change_password = tenant_update.must_change_password
    
    # Prepare tenant update data - only include fields that are not None
    update_data = {}
    if tenant_update.name is not None:
        update_data['name'] = tenant_update.name
    if tenant_update.category is not None:
        update_data['category'] = tenant_update.category.upper()
    if tenant_update.domain is not None:
        update_data['domain'] = tenant_update.domain
    if tenant_update.is_active is not None:
        update_data['is_active'] = tenant_update.is_active
    
    # Update tenant fields - only update fields that are explicitly provided (not None)
    if update_data:
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        db.commit()
        db.refresh(tenant)
    
    # Update admin user if admin fields are provided (only if not None)
    # Check if any admin field is explicitly provided
    has_admin_updates = (
        admin_username is not None or 
        admin_password is not None or 
        must_change_password is not None
    )
    
    if has_admin_updates:
        await _update_admin_user(
            tenant=tenant,
            tenant_id=tenant_id,
            admin_username=admin_username,
            admin_password=admin_password,
            must_change_password=must_change_password
        )
    
    # Handle logo upload if provided
    print("OK LET US PROCEED.... Check for logo file.")
    if logo_file:
        await _upload_tenant_logo_safe(
            tenant=tenant,
            tenant_id=tenant_id,
            logo_file=logo_file,
            global_db=db  # Pass global database session
        )
    
    # Enrich tenant with admin_username and logo_url before returning
    tenant = _enrich_tenant(db, tenant)
    return tenant


async def _update_admin_user(
    tenant: Tenant,
    tenant_id: int,
    admin_username: Optional[str],
    admin_password: Optional[str],
    must_change_password: Optional[bool]
) -> None:
    """Helper function to update admin user for a tenant"""
    from app.exceptions import ConflictError, ValidationError
    
    # Determine which database to use for the user
    user_mode = get_database_mode()
    if user_mode == 'shared':
        user_db = get_shared_db()()
        should_close = False
    else:
        # Use tenant-specific database
        TenantSessionLocal = get_tenant_db(tenant.name)
        user_db = TenantSessionLocal()
        should_close = True
    
    try:
        # Find existing admin user for this tenant
        admin_user = user_db.query(User).filter(
            User.institution_id == tenant_id,
            User.role == 'super_admin'
        ).first()
        
        if admin_user:
            # Track if any changes were made
            has_changes = False
            
            # Update existing admin user - only update fields that are not None
            if admin_username is not None:
                # Check if new username already exists (excluding current user)
                existing_username = user_db.query(User).filter(
                    User.username == admin_username,
                    User.id != admin_user.id
                ).first()
                if existing_username:
                    raise ConflictError(f"Username '{admin_username}' already exists")
                
                if admin_user.username != admin_username:
                    admin_user.username = admin_username
                    has_changes = True
                    # Update email if username changed
                    if tenant.domain:
                        admin_user.email = f'{admin_username}@{tenant.domain}'
            
            if admin_password is not None:
                admin_user.password = hash_password(admin_password)
                has_changes = True
            
            if must_change_password is not None:
                new_value = 'true' if must_change_password else 'false'
                if admin_user.must_change_password != new_value:
                    admin_user.must_change_password = new_value
                    has_changes = True
            
            # Ensure role and user_type are correct (always set these)
            if admin_user.role != 'super_admin':
                admin_user.role = 'super_admin'
                has_changes = True
            if admin_user.user_type != 'TENANT':
                admin_user.user_type = 'TENANT'
                has_changes = True
            if admin_user.institution_id != tenant_id:
                admin_user.institution_id = tenant_id
                has_changes = True
            
            # Only commit if there were actual changes
            if has_changes:
                user_db.commit()
                user_db.refresh(admin_user)
        else:
            # No admin user exists, create one if username and password provided
            if admin_username and admin_password:
                # Check if username already exists
                existing_username = user_db.query(User).filter(
                    User.username == admin_username
                ).first()
                if existing_username:
                    raise ConflictError(f"Username '{admin_username}' already exists")
                
                # Create new admin user
                new_admin_user = User(
                    institution_id=tenant_id,
                    firstname='Admin',
                    middlename='',
                    lastname=tenant.name,
                    gender='Other',
                    address='',
                    email=f'{admin_username}@{tenant.domain or tenant.name}',
                    phone='',
                    username=admin_username,
                    password=hash_password(admin_password),
                    role='super_admin',
                    user_type='TENANT',
                    is_active='active',
                    must_change_password='true' if (must_change_password is True) else 'false'
                )
                user_db.add(new_admin_user)
                user_db.commit()
                user_db.refresh(new_admin_user)
            elif admin_username or admin_password:
                # Username or password provided but not both
                raise ValidationError("Both username and password are required to create a new admin user")
    except (ConflictError, ValidationError):
        # Re-raise validation/conflict errors
        raise
    except Exception as e:
        from app.helpers.logger import logger
        logger.error(f"Error updating admin user for tenant {tenant.name}: {e}")
        raise
    finally:
        if should_close:
            user_db.close()

async def _upload_tenant_logo_safe(
    tenant: Tenant,
    tenant_id: int,
    logo_file: UploadFile,
    global_db: Session
) -> None:
    """Helper function to upload tenant logo with error handling"""
    from app.apis.uploads import upload_tenant_logo
    
    # Determine which database to use for tenant_settings
    mode = get_database_mode()
    if mode == 'shared':
        # Use shared database session
        settings_db = get_shared_db()()
        should_close_settings = False
    else:
        # Use tenant-specific database
        TenantSessionLocal = get_tenant_db(tenant.name)
        settings_db = TenantSessionLocal()
        should_close_settings = True
    
    try:
        # Upload logo using the existing upload function
        # Pass global_db so it can update the tenant table
        await upload_tenant_logo(
            db=settings_db,
            institution_id=tenant_id,
            file=logo_file,
            tenant_db=global_db  # Pass global database session for tenant table update
        )
    except Exception as e:
        from app.helpers.logger import logger
        logger.error(f"Error uploading logo for tenant {tenant_id}: {e}")
        # Don't fail the entire update if logo upload fails
        # The tenant update will still succeed
    finally:
        if should_close_settings:
            settings_db.close()

def delete_tenant(db: Session, tenant_id: int) -> bool:
    """Delete a tenant"""
    tenant = get_tenant_by_id(db, tenant_id)
    db.delete(tenant)
    db.commit()
    return True