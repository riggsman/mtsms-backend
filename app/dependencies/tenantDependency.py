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

def get_tenant(x_tenant_name: Optional[str] = Header(default=None, alias="X-Tenant-Name")):
    """
    Extracts and validates the tenant name from the request header.
    In shared mode, tenant name is optional.
    In multi_tenant mode, tenant name is required.
    """
    mode = get_database_mode()
    
    if mode == 'shared':
        # In shared mode, tenant name is optional - return None if not provided
        return x_tenant_name if x_tenant_name else None
    else:
        # In multi_tenant mode, tenant name is required
        if not x_tenant_name:
            raise HTTPException(status_code=400, detail="Tenant name is required in multi-tenant mode")
        
        # Validate tenant exists
        db = next(get_db_session())
        try:
            tenant = db.query(Tenant).filter(Tenant.name == x_tenant_name).first()
            if not tenant:
                raise NotFoundError(f"Tenant '{x_tenant_name}' not found")
        finally:
            db.close()
        
        return x_tenant_name

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
    mode = get_database_mode()
    
    try:
        if mode == 'shared':
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
                print(f"Database session opened for tenant '{tenant_name}' (MULTI-TENANT MODE)")
                
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