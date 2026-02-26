from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.sessionManager import create_tenant_database, get_tenant_db, get_shared_db, get_database_mode
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantRequest, TenantResponse, TenantUpdate
from app.helpers.pagination import paginate_query
from app.exceptions import NotFoundError, ConflictError, ValidationError
from app.authentication.authenticator import hash_password
from app.services.email_service import EmailService
from app.helpers.async_helper import run_async_safe

async def create_new_tenant(db: Session, tenant: TenantRequest):
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
    
    return new_tenant

def get_tenant_by_name(db: Session, name: str) -> Optional[Tenant]:
    """Get tenant by name"""
    tenant = db.query(Tenant).filter(Tenant.name == name).first()
    if tenant:
        # Get admin username
        tenant = _add_admin_username(db, tenant)
    return tenant

def get_tenant_by_id(db: Session, tenant_id: int) -> Tenant:
    """Get tenant by ID"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")
    # Get admin username
    tenant = _add_admin_username(db, tenant)
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

def get_all_tenants(
    db: Session,
    skip: int = 0,
    limit: int = 10
) -> tuple[List[Tenant], int]:
    """Get all tenants with pagination"""
    query = db.query(Tenant)
    tenants, total = paginate_query(query, page=(skip // limit) + 1, page_size=limit)
    # Add admin username to each tenant
    tenants = [_add_admin_username(db, tenant) for tenant in tenants]
    return tenants, total

def update_tenant(db: Session, tenant_id: int, tenant_update: TenantUpdate) -> Tenant:
    """Update a tenant and optionally update admin user"""
    tenant = get_tenant_by_id(db, tenant_id)
    
    # Extract admin user fields
    admin_username = tenant_update.admin_username
    admin_password = tenant_update.admin_password
    must_change_password = tenant_update.must_change_password
    
    # Remove admin fields from tenant update data
    update_data = tenant_update.dict(exclude_unset=True)
    update_data.pop('admin_username', None)
    update_data.pop('admin_password', None)
    update_data.pop('must_change_password', None)
    
    # Update tenant fields
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    
    # Update admin user if admin fields are provided
    if admin_username is not None or admin_password is not None or must_change_password is not None:
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
                # Update existing admin user
                if admin_username is not None:
                    # Check if new username already exists (excluding current user)
                    existing_username = user_db.query(User).filter(
                        User.username == admin_username,
                        User.id != admin_user.id
                    ).first()
                    if existing_username:
                        from app.exceptions import ConflictError
                        raise ConflictError(f"Username '{admin_username}' already exists")
                    admin_user.username = admin_username
                    # Update email if username changed
                    if tenant.domain:
                        admin_user.email = f'{admin_username}@{tenant.domain}'
                
                if admin_password is not None:
                    admin_user.password = hash_password(admin_password)
                
                if must_change_password is not None:
                    admin_user.must_change_password = 'true' if must_change_password else 'false'
                
                # Ensure role and user_type are correct
                admin_user.role = 'super_admin'
                admin_user.user_type = 'TENANT'
                admin_user.institution_id = tenant_id  # Ensure it's set correctly
                
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
                        from app.exceptions import ConflictError
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
                    from app.exceptions import ValidationError
                    raise ValidationError("Both username and password are required to create a new admin user")
        except Exception as e:
            from app.helpers.logger import logger
            logger.error(f"Error updating admin user for tenant {tenant.name}: {e}")
            # Re-raise the exception
            raise
        finally:
            if should_close:
                user_db.close()
    
    # Refresh tenant to get updated admin_username
    tenant = _add_admin_username(db, tenant)
    return tenant

def delete_tenant(db: Session, tenant_id: int) -> bool:
    """Delete a tenant"""
    tenant = get_tenant_by_id(db, tenant_id)
    db.delete(tenant)
    db.commit()
    return True