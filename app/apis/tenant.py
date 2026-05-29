import datetime
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
from app.helpers.user_roles import (
    role_column_contains_role,
    user_has_role,
    parse_roles_to_list,
)


def _is_premium_plan(plan: Optional[str]) -> bool:
    return bool(plan and "premium" in plan.strip().lower())


def _parse_optional_datetime_str(value: Optional[str]) -> Optional[datetime.datetime]:
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD or ISO format.")


def _resolve_billing_type_from_plan(db: Session, plan_name: Optional[str]) -> Optional[str]:
    if not plan_name or not str(plan_name).strip():
        return None
    from app.models.subscription_plan import SubscriptionPlan

    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.name == str(plan_name).strip())
        .first()
    )
    if plan and plan.billing_period:
        return str(plan.billing_period).strip()
    return None


def _apply_premium_billing_defaults(
    db: Session, tenant: Tenant, update_data: dict
) -> None:
    """Fill payment_date / subscription_started_at / billing_type for premium tenants when missing."""
    plan = (update_data.get("subscription_plan") or tenant.subscription_plan or "").strip()
    if not _is_premium_plan(plan):
        return
    anchor = (
        update_data.get("payment_date")
        or update_data.get("subscription_started_at")
        or tenant.payment_date
        or tenant.subscription_started_at
        or tenant.created_at
    )
    if not anchor:
        return
    if "payment_date" not in update_data and not tenant.payment_date:
        update_data["payment_date"] = anchor
    if "subscription_started_at" not in update_data and not tenant.subscription_started_at:
        update_data["subscription_started_at"] = anchor
    if "billing_type" not in update_data and not tenant.billing_type:
        resolved = _resolve_billing_type_from_plan(db, plan)
        update_data["billing_type"] = resolved or "monthly"


def backfill_premium_tenant_billing(db: Session) -> int:
    """Backfill missing billing fields for all premium tenants in the global DB."""
    updated = 0
    tenants = db.query(Tenant).filter(Tenant.subscription_plan.isnot(None)).all()
    for tenant in tenants:
        if not _is_premium_plan(tenant.subscription_plan):
            continue
        anchor = tenant.payment_date or tenant.subscription_started_at or tenant.created_at
        if not anchor:
            continue
        changed = False
        if not tenant.payment_date:
            tenant.payment_date = anchor
            changed = True
        if not tenant.subscription_started_at:
            tenant.subscription_started_at = anchor
            changed = True
        if not tenant.billing_type:
            resolved = _resolve_billing_type_from_plan(db, tenant.subscription_plan)
            tenant.billing_type = resolved or "monthly"
            changed = True
        if changed:
            updated += 1
    if updated:
        db.commit()
    return updated


def _check_tenant_contact_uniqueness(
    db: Session,
    *,
    email: Optional[str] = None,
    telephone: Optional[str] = None,
    exclude_tenant_id: Optional[int] = None,
) -> None:
    if email and str(email).strip():
        em = str(email).strip()
        q = db.query(Tenant).filter(Tenant.email == em)
        if exclude_tenant_id is not None:
            q = q.filter(Tenant.id != exclude_tenant_id)
        if q.first():
            raise ConflictError(f"Tenant with email '{em}' already exists")
    if telephone and str(telephone).strip():
        tel = str(telephone).strip()
        q = db.query(Tenant).filter(Tenant.telephone == tel)
        if exclude_tenant_id is not None:
            q = q.filter(Tenant.id != exclude_tenant_id)
        if q.first():
            raise ConflictError(f"Tenant with telephone '{tel}' already exists")


async def create_new_tenant(db: Session, tenant: TenantRequest, logo_file: Optional[UploadFile] = None):
    """Create a new tenant"""
    # Check if tenant already exists
    existing = get_tenant_by_name(db, tenant.name)
    if existing:
        raise ConflictError(f"Tenant with name '{tenant.name}' already exists")
    
    # Check if domain already exists
    if tenant.domain:
        existing_domain = db.query(Tenant).filter(Tenant.domain == tenant.domain).first()
        if existing_domain:
            raise ConflictError(f"Tenant with domain '{tenant.domain}' already exists")

    _check_tenant_contact_uniqueness(db, email=tenant.email, telephone=tenant.telephone)
    
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
        region=str(tenant.region).strip(),
        city=str(tenant.city).strip(),
        neighbourhood=str(tenant.neighbourhood).strip(),
        email=str(tenant.email).strip(),
        telephone=str(tenant.telephone).strip(),
        category=tenant.category.upper(),  # Ensure uppercase (HI or SI)
        domain=tenant.domain,
        database_url=tenant_database_url,
        is_active=tenant.is_active if tenant.is_active is not None else True,
        services_activated=False,
    )
    
    if tenant.subscription_plan:
        plan_name = tenant.subscription_plan.strip()
        new_tenant.subscription_plan = plan_name
        resolved_billing = _resolve_billing_type_from_plan(db, plan_name)
        if resolved_billing:
            new_tenant.billing_type = resolved_billing

    if tenant.billing_type and str(tenant.billing_type).strip():
        new_tenant.billing_type = str(tenant.billing_type).strip()

    started = _parse_optional_datetime_str(tenant.subscription_started_at)
    if started:
        new_tenant.subscription_started_at = started
        if _is_premium_plan(tenant.subscription_plan):
            new_tenant.payment_date = started
    elif _is_premium_plan(tenant.subscription_plan):
        now = datetime.datetime.utcnow()
        new_tenant.subscription_started_at = now
        new_tenant.payment_date = now

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
                existing_user.role = ['super_admin']
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
                    role=['super_admin'],
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
                            tenant_name=new_tenant.name,
                            admin_email=admin_email,
                            admin_username=tenant.admin_username,
                            admin_password=tenant.admin_password,
                            domain=new_tenant.domain,
                            subscription_plan=new_tenant.subscription_plan,
                            billing_type=new_tenant.billing_type,
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
            new_settings = TenantSettings(
                institution_id=tenant_id,
                branches_enabled=bool(getattr(tenant, "branches_enabled", None))
                if getattr(tenant, "branches_enabled", None) is not None
                else False,
            )
            settings_db.add(new_settings)
            settings_db.commit()
            settings_db.refresh(new_settings)
        else:
            # If settings exist, update branches_enabled only when provided.
            if getattr(tenant, "branches_enabled", None) is not None:
                existing_settings.branches_enabled = bool(tenant.branches_enabled)
                settings_db.commit()
                settings_db.refresh(existing_settings)

        # If the system admin requested initial branch creation during tenant setup,
        # create the first Branch row now (scoped to this tenant_id / institution_id).
        try:
            initial_branch_name = getattr(tenant, "initial_branch_name", None)
            branches_enabled = getattr(tenant, "branches_enabled", None)
            if bool(branches_enabled) and initial_branch_name and str(initial_branch_name).strip():
                from app.models.branch import Branch

                branch_name = str(initial_branch_name).strip()
                existing_branch = (
                    settings_db.query(Branch)
                    .filter(
                        Branch.institution_id == tenant_id,
                        Branch.name == branch_name,
                    )
                    .first()
                )

                if not existing_branch:
                    settings_db.add(
                        Branch(
                            institution_id=tenant_id,
                            name=branch_name,
                            code=None,
                            sort_order=0,
                            is_active=True,
                        )
                    )
                    settings_db.commit()
        except Exception as branch_err:
            from app.helpers.logger import logger
            logger.warning(
                f"Could not create initial branch for tenant {tenant.name}: {branch_err}"
            )

        # HI: seed application-level rows (Level 1–3, Masters 1–2, B.Tech cohort) for student registration.
        try:
            if new_tenant.category and str(new_tenant.category).upper() == "HI":
                from app.helpers.hi_degree_program_classes import seed_hi_application_level_classes

                seed_hi_application_level_classes(settings_db, tenant_id)
        except Exception as seed_err:
            from app.helpers.logger import logger

            logger.warning(
                "Could not seed HI application-level classes for tenant %s: %s",
                tenant.name,
                seed_err,
            )
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
                role_column_contains_role(db.get_bind(), User.role, 'super_admin'),
            ).first()
        else:
            # Need to query tenant-specific database
            try:
                TenantSessionLocal = get_tenant_db(tenant.name)
                tenant_db = TenantSessionLocal()
                try:
                    admin_user = tenant_db.query(User).filter(
                        User.institution_id == tenant.id,
                        role_column_contains_role(tenant_db.get_bind(), User.role, 'super_admin'),
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
            logo_url = get_file_url(tenant_settings.logo)
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


def _add_institution_contact(db: Session, tenant: Tenant) -> Tenant:
    """
  Set tenant.phone for API responses when institution telephone is empty.
  Preserve tenant.email / tenant.telephone from the tenants table (institution contact).
  Fall back to an active admin user only when institution fields are not set.
    """
    institution_email = (getattr(tenant, "email", None) or "").strip() or None
    institution_phone = (getattr(tenant, "telephone", None) or "").strip() or None
    try:
        mode = get_database_mode()
        mode_norm = str(mode or "shared").lower().strip()
        is_shared = mode_norm not in (
            "multi_tenant",
            "multi-tenant",
            "multitenant",
            "isolated",
        )

        if is_shared:
            users = (
                db.query(User)
                .filter(
                    User.institution_id == tenant.id,
                    User.deleted_at.is_(None),
                    User.is_active == "active",
                )
                .order_by(User.id.asc())
                .all()
            )
        else:
            try:
                TenantSessionLocal = get_tenant_db(tenant.name)
                tenant_db = TenantSessionLocal()
                try:
                    users = (
                        tenant_db.query(User)
                        .filter(
                            User.institution_id == tenant.id,
                            User.deleted_at.is_(None),
                            User.is_active == "active",
                        )
                        .order_by(User.id.asc())
                        .all()
                    )
                finally:
                    tenant_db.close()
            except Exception:
                users = []

        def pick_email_phone(user_list: List[User]) -> tuple[Optional[str], Optional[str]]:
            for u in user_list:
                roles = parse_roles_to_list(u.role)
                if "admin" in roles or "super_admin" in roles:
                    em = (u.email or "").strip() or None
                    ph = (u.phone or "").strip() or None
                    return em, ph
            if user_list:
                u = user_list[0]
                em = (u.email or "").strip() or None
                ph = (u.phone or "").strip() or None
                return em, ph
            return None, None

        admin_em, admin_ph = pick_email_phone(users)
        setattr(tenant, "email", institution_email or admin_em)
        setattr(tenant, "phone", institution_phone or admin_ph)
    except Exception:
        setattr(tenant, "email", institution_email)
        setattr(tenant, "phone", institution_phone)
    return tenant


def _enrich_tenant(db: Session, tenant: Tenant) -> Tenant:
    """Helper function to enrich tenant with admin_username and logo_url"""
    print("OK LET US PROCEED..... Enrich tenant with admin_username and logo_url.")
    tenant = _add_admin_username(db, tenant)
    tenant = _add_institution_contact(db, tenant)
    tenant = _add_logo_url(db, tenant)
    tenant = _add_branches_enabled(db, tenant)
    print("OK LET US PROCEED..... Enrichment complete. ", tenant.logo_url)
    return tenant


def _add_branches_enabled(db: Session, tenant: Tenant) -> Tenant:
    """
    Add branches_enabled flag from tenant_settings onto the Tenant response object.

    For shared mode we read from the shared database. For multi-tenant mode we
    read from the tenant-specific database.
    """
    try:
        from app.models.tenant_settings import TenantSettings

        mode = get_database_mode()
        if mode == "shared":
            settings_db = get_shared_db()()
            should_close = False
        else:
            TenantSessionLocal = get_tenant_db(tenant.name)
            settings_db = TenantSessionLocal()
            should_close = True

        try:
            ts = (
                settings_db.query(TenantSettings)
                .filter(TenantSettings.institution_id == tenant.id)
                .first()
            )
            tenant.branches_enabled = bool(ts.branches_enabled) if ts else False
        finally:
            if should_close:
                settings_db.close()
    except Exception:
        tenant.branches_enabled = False
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
    if tenant_update.region is not None:
        stripped = str(tenant_update.region).strip()
        if stripped:
            update_data['region'] = stripped
    if tenant_update.city is not None:
        stripped = str(tenant_update.city).strip()
        if stripped:
            update_data['city'] = stripped
    if tenant_update.neighbourhood is not None:
        stripped = str(tenant_update.neighbourhood).strip()
        if stripped:
            update_data['neighbourhood'] = stripped
    if tenant_update.email is not None:
        stripped = str(tenant_update.email).strip()
        if stripped:
            _check_tenant_contact_uniqueness(
                db, email=stripped, exclude_tenant_id=tenant_id
            )
            update_data['email'] = stripped
    if tenant_update.telephone is not None:
        stripped = str(tenant_update.telephone).strip()
        if stripped:
            _check_tenant_contact_uniqueness(
                db, telephone=stripped, exclude_tenant_id=tenant_id
            )
            update_data['telephone'] = stripped
    if tenant_update.category is not None:
        update_data['category'] = tenant_update.category.upper()
    if tenant_update.domain is not None:
        update_data['domain'] = tenant_update.domain
    if tenant_update.is_active is not None:
        update_data['is_active'] = tenant_update.is_active
        if tenant_update.is_active:
            update_data['suspension_reason'] = None
            update_data['suspended_at'] = None
    if tenant_update.fee_amount is not None:
        update_data['fee_amount'] = tenant_update.fee_amount
    if tenant_update.fee_deadline is not None:
        from datetime import datetime
        try:
            update_data['fee_deadline'] = datetime.fromisoformat(tenant_update.fee_deadline.replace('Z', '+00:00'))
        except ValueError:
            try:
                update_data['fee_deadline'] = datetime.strptime(tenant_update.fee_deadline, '%Y-%m-%d')
            except ValueError:
                raise ValidationError("Invalid fee_deadline format. Use YYYY-MM-DD or ISO format.")
    if tenant_update.subscription_plan is not None:
        stripped = (tenant_update.subscription_plan or "").strip()
        update_data["subscription_plan"] = stripped if stripped else None
        # Auto-set billing_type from subscription_plans table
        if stripped:
            from app.models.subscription_plan import SubscriptionPlan
            plan = db.query(SubscriptionPlan).filter(
                SubscriptionPlan.name == stripped
            ).first()
            if plan:
                update_data["billing_type"] = plan.billing_period
    if tenant_update.billing_type is not None:
        stripped_billing = (tenant_update.billing_type or "").strip()
        update_data["billing_type"] = stripped_billing if stripped_billing else None

    if tenant_update.payment_date is not None:
        from datetime import datetime

        raw_payment = (tenant_update.payment_date or "").strip()
        if not raw_payment:
            update_data["payment_date"] = None
        else:
            try:
                update_data["payment_date"] = datetime.fromisoformat(
                    raw_payment.replace("Z", "+00:00")
                )
            except ValueError:
                try:
                    update_data["payment_date"] = datetime.strptime(raw_payment, "%Y-%m-%d")
                except ValueError:
                    raise ValidationError(
                        "Invalid payment_date format. Use YYYY-MM-DD or ISO format."
                    )

    if tenant_update.subscription_started_at is not None:
        from datetime import datetime

        raw = (tenant_update.subscription_started_at or "").strip()
        if not raw:
            update_data["subscription_started_at"] = None
        else:
            try:
                update_data["subscription_started_at"] = datetime.fromisoformat(
                    raw.replace("Z", "+00:00")
                )
            except ValueError:
                try:
                    update_data["subscription_started_at"] = datetime.strptime(raw, "%Y-%m-%d")
                except ValueError:
                    raise ValidationError(
                        "Invalid subscription_started_at format. Use YYYY-MM-DD or ISO format."
                    )

    if (
        "subscription_started_at" in update_data
        and update_data["subscription_started_at"]
        and tenant_update.payment_date is None
        and "payment_date" not in update_data
    ):
        plan_name = (
            update_data.get("subscription_plan") or tenant.subscription_plan or ""
        ).strip().lower()
        if plan_name and _is_premium_plan(plan_name):
            update_data["payment_date"] = update_data["subscription_started_at"]

    _apply_premium_billing_defaults(db, tenant, update_data)

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

    # Update tenant_settings.branches_enabled if explicitly provided
    if getattr(tenant_update, "branches_enabled", None) is not None:
        from app.models.tenant_settings import TenantSettings

        mode = get_database_mode()
        if mode == "shared":
            settings_db = get_shared_db()()
            should_close_settings = False
        else:
            TenantSessionLocal = get_tenant_db(tenant.name)
            settings_db = TenantSessionLocal()
            should_close_settings = True

        try:
            existing_settings = settings_db.query(TenantSettings).filter(
                TenantSettings.institution_id == tenant_id
            ).first()

            if existing_settings:
                existing_settings.branches_enabled = bool(tenant_update.branches_enabled)
                settings_db.commit()
                settings_db.refresh(existing_settings)
            else:
                new_settings = TenantSettings(
                    institution_id=tenant_id,
                    branches_enabled=bool(tenant_update.branches_enabled),
                )
                settings_db.add(new_settings)
                settings_db.commit()
                settings_db.refresh(new_settings)
        finally:
            if should_close_settings:
                settings_db.close()
    
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
            role_column_contains_role(user_db.get_bind(), User.role, 'super_admin'),
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
            if not user_has_role(admin_user, 'super_admin'):
                admin_user.role = ['super_admin']
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
                    role=['super_admin'],
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

def suspend_tenant(
    db: Session,
    tenant_id: int,
    reason: str,
    *,
    actor_user_id: int | None = None,
) -> Tenant:
    """Mark tenant inactive and record suspension reason (blocks tenant user login)."""
    from app.services.tenant_audit_service import record_tenant_audit_event

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")
    r = (reason or "").strip()
    if not r:
        raise ValidationError("Suspension reason is required.")
    tenant.is_active = False
    tenant.suspension_reason = r[:4000]
    tenant.suspended_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(tenant)
    from app.helpers.tenant_activation_cache import invalidate_tenant_access_cache

    invalidate_tenant_access_cache(tenant.id)
    record_tenant_audit_event(
        db,
        tenant_id=tenant.id,
        action="suspend",
        reason=r,
        actor_user_id=actor_user_id,
    )
    return _enrich_tenant(db, tenant)


def resume_tenant(
    db: Session,
    tenant_id: int,
    *,
    actor_user_id: int | None = None,
) -> Tenant:
    """Re-activate tenant and clear suspension metadata."""
    from app.services.tenant_audit_service import record_tenant_audit_event

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise NotFoundError(f"Tenant with ID {tenant_id} not found")
    tenant.is_active = True
    tenant.suspension_reason = None
    tenant.suspended_at = None
    db.commit()
    db.refresh(tenant)
    from app.helpers.tenant_activation_cache import invalidate_tenant_access_cache

    invalidate_tenant_access_cache(tenant.id)
    record_tenant_audit_event(
        db,
        tenant_id=tenant.id,
        action="resume",
        actor_user_id=actor_user_id,
    )
    return _enrich_tenant(db, tenant)


def delete_tenant(db: Session, tenant_id: int) -> bool:
    """Delete a tenant"""
    tenant = get_tenant_by_id(db, tenant_id)
    db.delete(tenant)
    db.commit()
    return True