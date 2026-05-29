from fastapi import FastAPI, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import ExpiredSignatureError, JWTError, jwt
from datetime import datetime, timedelta, timezone
import re
from app.conf.config import settings
from app.models.user import User
from app.database.base import get_db_session

# Argon2 context for hashing (more secure than bcrypt)
# Argon2id is the recommended variant for password hashing
# We support both argon2 and bcrypt for backward compatibility during migration
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


# Function to hash passwords
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Function to verify passwords
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    Supports both argon2 and bcrypt hash formats.
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        # Ensure both are strings
        plain_password = str(plain_password).strip()
        hashed_password = str(hashed_password).strip()
        
        # Check if hash looks valid (should start with $argon2 or $2b$ for bcrypt)
        if not (hashed_password.startswith('$argon2') or hashed_password.startswith('$2a$') or 
                hashed_password.startswith('$2b$') or hashed_password.startswith('$2y$')):
            print(f"Warning: Hash format doesn't look valid: {hashed_password[:30]}...")
            # Still try to verify in case it's a different format
        
        # Verify using passlib context (supports both argon2 and bcrypt)
        result = pwd_context.verify(plain_password, hashed_password)
        
        if not result:
            # Log for debugging (but don't expose sensitive info)
            print(f"Password verification failed. Hash prefix: {hashed_password[:30]}...")
            print(f"Password verification failed. Hash prefix: {hashed_password}")
            print(f"ENTERED PASSWORD {hash_password(plain_password)}")

        
        return result
    except ValueError as e:
        # This might happen if the hash format is completely invalid
        print(f"Password verification ValueError: {e}")
        print(f"Hash format: {hashed_password[:50] if hashed_password else 'None'}...")
        return False
    except Exception as e:
        # Log the error for debugging
        print(f"Password verification error: {type(e).__name__}: {e}")
        print(f"Hash format: {hashed_password[:50] if hashed_password else 'None'}...")
        return False


def _get_effective_access_token_expire_minutes():
    """Get effective access token expiration minutes (cached settings, then env, then config)."""
    from app.helpers.system_settings_cache import get_effective_access_token_expire_minutes

    return get_effective_access_token_expire_minutes()


def _get_effective_refresh_token_expire_days():
    """Get effective refresh token expiration days (cached settings, then env, then config)."""
    from app.helpers.system_settings_cache import get_effective_refresh_token_expire_days

    return get_effective_refresh_token_expire_days()


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    # Get effective expiration from database or environment
    expire_minutes = _get_effective_access_token_expire_minutes()
    print(f"[Authenticator] Creating access token with expiry: {expire_minutes} minutes")
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=expire_minutes))
    to_encode.update({"exp": expire.timestamp()})  # Convert to Unix timestamp
    print(f"[Authenticator] Token exp timestamp: {expire.timestamp()} (local: {expire})")

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_and_decode_access_token(token: str, raise_exception: bool = False):
    """
    Verify and decode JWT token
    Returns: {"success": True, "data": payload} or {"error": "error message"}
    If raise_exception is True, raises HTTPException instead of returning error dict
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Verify expiration time manually
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
            error_msg = "Token has expired"
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )
            return {"error": error_msg}
        print("DECODE TOKEN PAYLOAD  ",payload)

        return {"success": True, "data": payload}

    except ExpiredSignatureError:
        error_msg = "Token has expired"
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg
            )
        return {"error": error_msg}
    except JWTError as e:
        error_msg = "Invalid token"
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg
            )
        return {"error": error_msg}


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, ""


def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    
    # Get effective expiration from database or environment
    expire_days = _get_effective_refresh_token_expire_days()
    print(f"[Authenticator] Creating refresh token with expiry: {expire_days} days")
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(days=expire_days))
    to_encode.update({"exp": expire.timestamp()})  # Convert to Unix timestamp

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


class AuthUser:
    def __init__(self, user):
        self.id = user.id
        self.user = user
        self.institution_id = user.institution_id
        self.branch_id = user.branch_id
        self.username = user.username
        self.email = user.email
        self.role = user.role


def auth_guard(
    authorization: str = Header(None, alias="Authorization"),
    db: Session = Depends(get_db_session)
) -> AuthUser:
    """
    Dependency for authentication - extracts user from JWT token
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    result = verify_and_decode_access_token(token, raise_exception=True)
    
    payload = result.get("data", {})
    user_id = int(payload.get("sub"))
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if user.is_active != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active"
        )
    
    return AuthUser(user)

