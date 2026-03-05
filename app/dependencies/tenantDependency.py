# from fastapi import HTTPException,Depends,Header

# from app.database.sessionManager import get_tenant_db
# # from app.database.sessionManager import get_tenant_db

# def get_tenant(tenant_name:str = Header(...,alias="X-Tenant-Name")):
#     if not tenant_name:
#         raise HTTPException(status_code=400,detail="Tenant name is required")
#     return tenant_name

# def get_db(tenant_name:str = Depends(get_tenant)):
#     db = get_tenant_db(tenant_name)
#     print("SUPPOSED DATABASE SESSION: %s" % db)
#     try:
#         yield db
#     finally:
#         db.close()
 

    # except Exception as e:
    #    raise ValueError("Error getting database for tenant %s: %s %s" % (tenant_name, e, db))
    # finally:
    #     db.close()


from fastapi import HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.database.sessionManager import get_tenant_db, get_shared_db, get_database_mode, get_db_session_for_mode
from app.database.base import get_db_session
from app.models.tenant import Tenant
from app.exceptions import NotFoundError
import logging

logger = logging.getLogger(__name__)

def get_tenant(
    x_tenant_name: Optional[str] = Header(default=None, alias="X-Tenant-Name"),
    authorization: Optional[str] = Header(default=None, alias="Authorization")
):
    """
    Extracts and validates the tenant name from the request header or authenticated user's session.
    Priority:
    1. Try to get tenant from authenticated user's session (via JWT token institution_id)
    2. Fall back to X-Tenant-Name header
    3. Can accept either tenant name or domain.
    In shared mode, tenant name is optional and validation is skipped.
    In multi_tenant mode, tenant name is required and must exist.
    """
    # Default to shared mode - only validate if explicitly in multi-tenant mode
    mode = 'shared'
    mode_normalized = 'shared'
    is_multi_tenant = False
    
    try:
        detected_mode = get_database_mode()
        if detected_mode:
            mode = detected_mode
            mode_normalized = str(detected_mode).lower().strip()
            # Only treat as multi-tenant if explicitly one of these values
            is_multi_tenant = mode_normalized in ['multi_tenant', 'multi-tenant', 'multitenant', 'isolated']
    except Exception as mode_error:
        # If mode detection fails, default to shared mode (safer)
        print(f"[get_tenant] Error detecting database mode: {mode_error}, defaulting to shared")
        logger.warning(f"[get_tenant] Error detecting database mode: {mode_error}, defaulting to shared")
        mode = 'shared'
        mode_normalized = 'shared'
        is_multi_tenant = False
    
    # Try to get tenant from authenticated user's session (via JWT token)
    tenant_from_session = None
    if authorization:
        try:
            # Extract token from "Bearer <token>"
            scheme, token = authorization.split()
            if scheme.lower() == "bearer":
                # Decode token to get institution_id (without verification for now, just to get tenant)
                from jose import jwt
                from app.conf.config import settings
                try:
                    # Try to decode without verification first to get payload
                    payload_unverified = jwt.decode(token, options={"verify_signature": False})
                    institution_id = payload_unverified.get("institution_id")
                    
                    if institution_id:
                        # Verify token properly and get tenant from institution_id
                        from app.authentication.authenticator import verify_and_decode_access_token
                        result = verify_and_decode_access_token(token)
                        
                        if result.get("success"):
                            payload = result["data"]
                            institution_id = payload.get("institution_id")
                            
                            if institution_id:
                                # Get tenant from institution_id (institution_id maps to tenant.id)
                                from app.database.sessionManager import DefaultSessionLocal
                                db = DefaultSessionLocal()
                                try:
                                    tenant = db.query(Tenant).filter(
                                        Tenant.id == institution_id,
                                        Tenant.is_active == True
                                    ).first()
                                    
                                    if tenant:
                                        tenant_from_session = tenant.domain or tenant.name
                                        print(f"[get_tenant] Found tenant from session: {tenant_from_session} (institution_id: {institution_id})")
                                        logger.debug(f"[get_tenant] Found tenant from session: {tenant_from_session} (institution_id: {institution_id})")
                                except Exception as e:
                                    print(f"[get_tenant] Error fetching tenant from session: {e}")
                                    logger.warning(f"[get_tenant] Error fetching tenant from session: {e}")
                                finally:
                                    db.close()
                except Exception as e:
                    # Token might be invalid or expired, continue with header-based approach
                    print(f"[get_tenant] Could not decode token for tenant extraction: {e}")
                    logger.debug(f"[get_tenant] Could not decode token for tenant extraction: {e}")
        except (ValueError, AttributeError) as e:
            # Invalid authorization header format, continue with header-based approach
            print(f"[get_tenant] Invalid authorization header format: {e}")
            logger.debug(f"[get_tenant] Invalid authorization header format: {e}")
    
    # Use tenant from session if available, otherwise use header
    final_tenant_name = tenant_from_session or x_tenant_name
    
    # Debug logging
    print(f"[get_tenant] Mode: {mode}, Normalized: {mode_normalized}, Is Multi-Tenant: {is_multi_tenant}")
    print(f"[get_tenant] Tenant from session: {tenant_from_session}, X-Tenant-Name header: {x_tenant_name}, Final: {final_tenant_name}")
    logger.debug(f"[get_tenant] Mode: {mode}, Normalized: {mode_normalized}, Is Multi-Tenant: {is_multi_tenant}")
    logger.debug(f"[get_tenant] Tenant from session: {tenant_from_session}, X-Tenant-Name header: {x_tenant_name}, Final: {final_tenant_name}")
    
    # ALWAYS default to shared mode behavior unless explicitly in multi-tenant mode
    # This is the safest approach - only validate tenant if we're CERTAIN we're in multi-tenant mode
    if not is_multi_tenant:
        # In shared mode (or any mode that's not explicitly multi-tenant), tenant name is optional
        # Return as-is without validation - used for filtering data by institution_id
        print(f"[get_tenant] Shared mode (mode='{mode}', normalized='{mode_normalized}') - returning tenant name without validation: {final_tenant_name}")
        logger.debug(f"[get_tenant] Shared mode - skipping tenant validation, returning: {final_tenant_name}")
        return final_tenant_name if final_tenant_name else None
    else:
        # In multi_tenant mode, tenant name is required and must exist
        print(f"[get_tenant] Multi-tenant mode detected - validating tenant: {final_tenant_name}")
        logger.debug(f"[get_tenant] Multi-tenant mode - validating tenant: {final_tenant_name}")
        # In multi_tenant mode, tenant name is required
        if not final_tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name is required in multi-tenant mode. Please ensure you are authenticated or provide X-Tenant-Name header.")
        
        # Validate tenant exists - try by name first, then by domain (case-insensitive)
        # Use DefaultSessionLocal for tenant lookup (tenants are stored in global database)
        from app.database.sessionManager import DefaultSessionLocal
        db = DefaultSessionLocal()
        try:
            # Normalize input (lowercase for comparison)
            final_tenant_normalized = final_tenant_name.lower().strip() if final_tenant_name else None
            
            # First try to find by name (case-insensitive)
            from sqlalchemy import func
            tenant = db.query(Tenant).filter(
                func.lower(Tenant.name) == final_tenant_normalized
            ).first()
            
            # If not found by name, try by domain (case-insensitive, only if domain is set)
            if not tenant:
                tenant = db.query(Tenant).filter(
                    Tenant.domain.isnot(None),
                    Tenant.domain != '',
                    func.lower(Tenant.domain) == final_tenant_normalized
                ).first()
            
            if not tenant:
                # Try to get more helpful error info - list available tenants (for debugging)
                try:
                    all_tenants = db.query(Tenant).filter(Tenant.is_active == True).all()
                    tenant_names = [t.name for t in all_tenants[:5]]  # Limit to first 5
                    tenant_domains = [t.domain for t in all_tenants if t.domain][:5]
                    error_detail = f"Tenant '{final_tenant_name}' not found (checked by name and domain)."
                    if tenant_names:
                        error_detail += f" Available tenant names: {', '.join(tenant_names)}"
                    if tenant_domains:
                        error_detail += f" Available domains: {', '.join(tenant_domains)}"
                except Exception:
                    error_detail = f"Tenant '{final_tenant_name}' not found (checked by name and domain). Please verify the tenant exists and the domain/name is correct."
                
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=404,
                    detail=error_detail
                )
            
            # Return the tenant name (not domain) for database lookup
            # The database is keyed by tenant name, not domain
            return tenant.name
        finally:
            db.close()

def get_db_for_admin():
    """
    Dependency to get the shared database session for admin routes.
    This bypasses tenant dependency and always uses the shared/global database.
    """
    try:
        db = get_shared_db()()
        print(f"Database session opened (ADMIN ROUTE - SHARED MODE)")
        yield db
    except HTTPException as http_error:
        # Re-raise HTTPExceptions (like 401 for token expiration) without wrapping
        raise http_error
    except Exception as db_error:
        print(f"Error creating shared database session for admin route: {db_error}")
        import traceback
        traceback.print_exc()
        # Check if the error is a token expiration error
        error_str = str(db_error).lower()
        if '401' in error_str or ('token' in error_str and 'expired' in error_str):
            # If it's a token expiration error, return 401 instead of 500
            raise HTTPException(
                status_code=401, 
                detail="Token has expired"
            )
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to establish database connection (shared mode): {str(db_error)}"
        )
    finally:
        if 'db' in locals():
            try:
                db.close()
                print(f"Database session closed (ADMIN ROUTE - SHARED MODE)")
            except Exception as close_error:
                print(f"Error closing database session: {close_error}")

def get_db(tenant_name: Optional[str] = Depends(get_tenant)):
    """
    Dependency to get the appropriate database session based on mode.
    - In shared mode: returns shared database session (tenant_name is ignored)
    - In multi_tenant mode: returns tenant-specific database session (tenant_name is required)
    """
    # Default to shared mode - safer approach
    mode = 'shared'
    try:
        detected_mode = get_database_mode()
        if detected_mode:
            mode_normalized = str(detected_mode).lower().strip()
            # Only use multi-tenant mode if explicitly set
            if mode_normalized in ['multi_tenant', 'multi-tenant', 'multitenant', 'isolated']:
                mode = detected_mode
            else:
                mode = 'shared'
    except Exception as mode_error:
        # If mode detection fails, default to shared mode (safer)
        print(f"[get_db] Error detecting database mode: {mode_error}, defaulting to shared")
        mode = 'shared'
    
    print(f"[get_db] Using database mode: {mode}, tenant_name: {tenant_name}")
    
    try:
        # Normalize mode check - treat anything not explicitly multi-tenant as shared
        mode_normalized = str(mode).lower().strip() if mode else 'shared'
        is_multi_tenant = mode_normalized in ['multi_tenant', 'multi-tenant', 'multitenant', 'isolated']
        
        if not is_multi_tenant:
            # Use shared database
            try:
                db = get_shared_db()()
                print(f"Database session opened (SHARED MODE)")
                yield db
            except HTTPException as http_error:
                # Re-raise HTTPExceptions (like 401 for token expiration) without wrapping
                raise http_error
            except Exception as db_error:
                print(f"Error creating shared database session: {db_error}")
                import traceback
                traceback.print_exc()
                # Check if the error is a token expiration error
                error_str = str(db_error).lower()
                if '401' in error_str or ('token' in error_str and 'expired' in error_str):
                    # If it's a token expiration error, return 401 instead of 500
                    raise HTTPException(
                        status_code=401, 
                        detail="Token has expired"
                    )
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to establish database connection (shared mode): {str(db_error)}"
                )
        else:
            # Use tenant-specific database
            if not tenant_name:
                raise HTTPException(status_code=400, detail="Tenant name is required in multi-tenant mode")
            
            try:
                TenantSessionLocal = get_tenant_db(tenant_name)
                print(f"[get_db] Database session opened for tenant '{tenant_name}' (MULTI-TENANT MODE)")
                
                db = TenantSessionLocal()
                yield db
            except Exception as db_error:
                print(f"Error creating tenant database session for '{tenant_name}': {db_error}")
                import traceback
                traceback.print_exc()
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to establish database connection for tenant '{tenant_name}': {str(db_error)}"
                )

    except HTTPException as e:
        # Re-raise HTTPExceptions (including 401 for token expiration)
        # Check if it's a token expiration error
        error_str = str(e.detail).lower() if e.detail else str(e).lower()
        if e.status_code == 401 or ('token' in error_str and 'expired' in error_str):
            # Preserve 401 status for token expiration
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        raise e
    except Exception as e:
        # Handle unexpected errors
        print(f"Unexpected error creating database session: {e}")
        import traceback
        traceback.print_exc()
        # Check if the error is a token expiration error
        error_str = str(e).lower()
        if '401' in error_str or ('token' in error_str and 'expired' in error_str):
            # If it's a token expiration error, return 401 instead of 500
            raise HTTPException(
                status_code=401, 
                detail="Token has expired"
            )
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to establish database connection: {str(e)}"
        )
    finally:
        # Ensure the session is closed
        if 'db' in locals():
            try:
                db.close()
                mode_str = "SHARED MODE" if mode == 'shared' else f"tenant '{tenant_name}' (MULTI-TENANT MODE)"
                print(f"Database session closed ({mode_str})")
            except Exception as close_error:
                print(f"Error closing database session: {close_error}")