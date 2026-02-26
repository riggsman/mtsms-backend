import argon2
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.authentication.authenticator import create_access_token, create_refresh_token, verify_and_decode_access_token, verify_password
from app.models.user import User
from app.schemas.login import LoginRequest, LoginResponse
from app.database.base import get_db_session



async def new_login(loginRequest: LoginRequest, db: Session, tenant_name: str = None):
    if not loginRequest.username or not loginRequest.password:
        raise HTTPException(status_code=400, detail="Missing username or password")
    else:
        # Try to find user by username first, then by email
        user = db.query(User).filter(User.username == loginRequest.username).first()
        if not user:
            # If not found by username, try email
            user = db.query(User).filter(User.email == loginRequest.username).first()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid username or password")
        
        if not verify_password(loginRequest.password, user.password):
            raise HTTPException(status_code=400, detail="Invalid username or password")
        
        # Get tenant name and domain from institution_id if available
        # System admins (roles starting with 'system_') don't need tenant
        tenant_name_from_user = None
        tenant_domain_from_user = None
        is_system_admin = user.role and user.role.startswith('system_')
        
        # Always fetch tenant information from database using institution_id
        if not is_system_admin and user.institution_id:
            from app.models.tenant import Tenant
            global_db = next(get_db_session())
            try:
                tenant = global_db.query(Tenant).filter(Tenant.id == user.institution_id).first()
                if tenant:
                    # Always use database values for tenant name and domain
                    tenant_name_from_user = tenant.name
                    tenant_domain_from_user = tenant.domain
                    # Log for debugging
                    print(f"Fetched tenant from database - Name: {tenant_name_from_user}, Domain: {tenant_domain_from_user}")
            except Exception as e:
                print(f"Error fetching tenant from database: {e}")
            finally:
                global_db.close()
        
        # Prioritize database values over request parameter
        # System admins don't require tenant name
        final_tenant_name = tenant_name_from_user if tenant_name_from_user else (tenant_name if not is_system_admin else None)
        final_domain = tenant_domain_from_user  # Always use domain from database if available
        
        data = {
            "sub": user.id.__str__(),
            "username": user.firstname + " " + user.lastname,
            "roles": user.role,
            "institution_id": user.institution_id
        }
        
        # Prepare user info for response
        from app.schemas.login import UserInfo
        user_info = UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            firstname=user.firstname,
            lastname=user.lastname,
            tenantName=final_tenant_name,
            domain=final_domain,
            institution_id=user.institution_id,
            mustChangePassword=getattr(user, 'must_change_password', 'false') == "true"
        )
        
        return LoginResponse(
            access_token=create_access_token(data), 
            refresh_token=create_refresh_token(data),
            token_type="bearer",
            user=user_info,
            tenantName=final_tenant_name,
            domain=final_domain
        )
    

async def verify_token(token: str):
    return verify_and_decode_access_token(token)

async def refresh_access_token(refresh_token: str):
    """Refresh access token using refresh token"""
    from app.authentication.authenticator import verify_and_decode_access_token, create_access_token, create_refresh_token
    
    # Verify the refresh token
    try:
        token_result = verify_and_decode_access_token(refresh_token, raise_exception=True)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    if not token_result.get("success"):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Extract user data from refresh token
    payload = token_result.get("data")
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")
    
    # Get user from database to ensure user still exists
    # Use global database session
    db = next(get_db_session())
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Create new tokens with same user data
        data = {
            "sub": str(user.id),
            "username": user.firstname + " " + user.lastname,
            "roles": user.role,
            "institution_id": user.institution_id
        }
        
        from app.schemas.login import RefreshTokenResponse
        return RefreshTokenResponse(
            access_token=create_access_token(data),
            refresh_token=create_refresh_token(data),
            token_type="bearer"
        )
    finally:
        db.close()
    
#     hashed_password = hash_password(password)
#     user_id = len(fake_users_db) + 1
#     fake_users_db[username] = User(id=user_id, username=username, hashed_password=hashed_password)
    
#     return {"msg": "User registered successfully"}

# Example endpoint to login a user and return a JWT token
# @app.post("/login")
# async def login(username: str, password: str):
   
#     if not user or not verify_password(password, user.hashed_password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")
    
#     access_token = create_access_token(data={"sub": user.id})
#     return {"access_token": access_token, "token_type": "bearer"}