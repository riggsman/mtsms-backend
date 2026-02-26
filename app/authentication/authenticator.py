from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import ExpiredSignatureError, JWTError, jwt
from datetime import datetime, timedelta, timezone
import re
from app.conf.config import settings

# Argon2 context for hashing (more secure than bcrypt)
# Argon2id is the recommended variant for password hashing
# We support both argon2 and bcrypt for backward compatibility during migration
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


class User:
    def __init__(self, id: int, username: str, hashed_password: str):
        self.id = id
        self.username = username
        self.hashed_password = hashed_password


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

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    # Ensure expiration is correctly set
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire.timestamp()})  # Convert to Unix timestamp

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
    
    # Ensure expiration is correctly set
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire.timestamp()})  # Convert to Unix timestamp

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

