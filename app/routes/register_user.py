# # from fastapi import FastAPI,APIRouter,Depends, HTTPException
# # from sqlalchemy.orm import Session
# # from app.authentication.authenticator import hash_password
# # from app.database.sessionManager import get_tenant_db
# # from app.models.user import User
# # from app.schemas.register_user import RegisterRequest
# # from app.schemas.tenant import TenantRequest, TenantResponse
# # from app.database.base import get_db_session
# # from app.dependencies.tenantDependency import get_db, get_tenant

# # db = get_db # we will use this in the route


# # register = APIRouter()



# # @register.post("/register") #  , ,response_model=TenantResponse
# # async def new_user(register_request: RegisterRequest,db:Session = Depends(get_db)):
# #     all_users = db.query(User).filter(User.username == register_request.username).first()
# #     if all_users:
# #         raise HTTPException(status_code=400, detail="Username already registered")
# #     else:
# #         hashed_password = hash_password(register_request.password)
# #         newUser = User(
# #             firstname=register_request.firstname,
# #             middlename=register_request.middlename,
# #             lastname=register_request.lastname,
# #             institution_id=9,
# #             gender=register_request.gender,
# #             address = register_request.address,
# #             email = register_request.email,
# #             phone = register_request.phone,
# #             username=register_request.username, 
# #             password=hashed_password,
# #             role = register_request.role
# #             )
# #         db.add(newUser)
# #         db.commit()
# #         db.refresh(newUser)
# #         db.close()
        
    
# #         return {"msg": f"User registered successfully {newUser.id}"}

# from fastapi import FastAPI, APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from app.authentication.authenticator import hash_password
# from app.database.sessionManager import get_db, get_tenant_session
# from app.models.user import User
# from app.schemas.register_user import RegisterRequest

# register = APIRouter()

# @register.post("/register")
# async def new_user(register_request: RegisterRequest, db: Session = Depends(get_db), tenant_session: Session = Depends(get_tenant_session)):
#     all_users = db.query(User).filter(User.username == register_request.username).first()
#     if all_users:
#         raise HTTPException(status_code=400, detail="Username already registered")
    
#     hashed_password = hash_password(register_request.password)
#     newUser = User(
#         firstname=register_request.firstname,
#         middlename=register_request.middlename,
#         lastname=register_request.lastname,
#         institution_id=9,
#         gender=register_request.gender,
#         address=register_request.address,
#         email=register_request.email,
#         phone=register_request.phone,
#         username=register_request.username, 
#         password=hashed_password,
#         role=register_request.role
#     )
    
#     db.add(newUser)
#     db.commit()
#     db.refresh(newUser)
    
#     return {"msg": f"User registered successfully {newUser.id}"}

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.authentication.authenticator import hash_password, validate_password_strength
from app.dependencies.tenantDependency import get_db, get_tenant
from app.database.base import get_db_session
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.register_user import RegisterRequest, RegisterResponse
from app.models.role import UserRole
from app.exceptions import ConflictError, ValidationError
from app.helpers.logger import logger

register = APIRouter()

@register.post("/register")
async def new_user(
    register_request: RegisterRequest,
    tenant_name: str = Depends(get_tenant),
    db: Session = Depends(get_db)  # Use the tenant-specific session
):
    """
    Register a new super administrator account (requires X-Tenant-Name header)
    
    Note: This endpoint is intended for registering super_admin accounts only.
    Other roles should be created through the User Management interface by existing administrators.
    
    Steps:
    1. Tenant Information: tenant_name (from header), email, address
    2. Personal Information: firstname, middlename, lastname, gender, phone
    3. Account Setup: username, role (super_admin), password
    """
    # Validate password strength
    is_valid, error_msg = validate_password_strength(register_request.password)
    if not is_valid:
        raise ValidationError(error_msg)
    
    # Validate role - only super_admin can register through this endpoint
    if not UserRole.has_value(register_request.role):
        raise ValidationError(f"Invalid role. Allowed roles: {UserRole.get_all_roles()}")
    
    if register_request.role != UserRole.SUPER_ADMIN.value:
        raise ValidationError("Registration is only available for super_admin role. Other roles must be created by existing administrators through the User Management interface.")
    
    # Check if the username already exists
    existing_user = db.query(User).filter(User.username == register_request.username).first()
    if existing_user:
        raise ConflictError("Username already registered")
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == register_request.email).first()
    if existing_email:
        raise ConflictError("Email already registered")
    
    # Get tenant to extract institution_id, or create it if it doesn't exist
    global_db = next(get_db_session())
    try:
        # Use tenant_name from request body if provided, otherwise from header
        actual_tenant_name = register_request.tenant_name or tenant_name
        domain = register_request.domain or (actual_tenant_name.lower().replace(' ', '') if actual_tenant_name else None)
        
        # Validate domain format
        if domain:
            import re
            if not re.match(r'^[a-z0-9-]+$', domain):
                raise ValidationError("Domain must contain only lowercase letters, numbers, and hyphens")
        
        tenant = global_db.query(Tenant).filter(
            (Tenant.name == actual_tenant_name) | (Tenant.domain == domain)
        ).first()
        
        if not tenant:
            # Auto-create tenant if it doesn't exist (for easier registration flow)
            # Generate a default database URL for the tenant
            default_db_url = f"mysql+pymysql://root@localhost/{domain or actual_tenant_name}"
            
            new_tenant = Tenant(
                name=actual_tenant_name,
                domain=domain,
                database_url=default_db_url
            )
            global_db.add(new_tenant)
            global_db.commit()
            global_db.refresh(new_tenant)
            tenant = new_tenant
            logger.info(f"Auto-created tenant: {actual_tenant_name} with domain: {domain}")
        else:
            # Update domain if not set
            if domain and not tenant.domain:
                tenant.domain = domain
                global_db.commit()
                logger.info(f"Updated tenant {actual_tenant_name} with domain: {domain}")
        
        institution_id = tenant.id
    finally:
        global_db.close()
    
    # Values are already normalized by validators
    middlename = register_request.middlename  # Already None if empty
    address = register_request.address  # Already validated and stripped
    
    # Create a new user
    # Registration through tenant endpoint is always TENANT user_type
    hashed_password = hash_password(register_request.password)
    newUser = User(
        firstname=register_request.firstname,  # Already stripped by validator
        middlename=middlename,
        lastname=register_request.lastname,  # Already stripped by validator
        institution_id=institution_id,
        gender=register_request.gender,
        address=address,  # Already validated and stripped
        email=register_request.email.lower().strip(),
        phone=register_request.phone,  # Already stripped by validator
        username=register_request.username.lower(),  # Already stripped by validator
        password=hashed_password,
        role=register_request.role.lower(),
        user_type="TENANT",  # Registration through tenant endpoint is always TENANT
        is_active="active"
    )

    # Add and commit the new user
    db.add(newUser)
    db.commit()
    db.refresh(newUser)

    # Return response with message for frontend compatibility
    return {
        "msg": "User registered successfully",
        "user_id": newUser.id,
        "firstname": newUser.firstname,
        "middlename": newUser.middlename,
        "lastname": newUser.lastname,
        "gender": newUser.gender,
        "address": newUser.address,
        "email": newUser.email,
        "phone": newUser.phone,
        "role": newUser.role,
        "username": newUser.username
    }