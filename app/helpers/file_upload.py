"""
Helper module for handling file uploads with tenant domain prefixing
"""
import os
import uuid
from typing import Optional, Tuple
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from starlette.requests import Request
from pathlib import Path
import re

# Allowed file types for different upload categories
ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
}

ALLOWED_LOGO_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml', 'image/webp'
}

ALLOWED_PROFILE_PICTURE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'
}

ALLOWED_NOTE_FILE_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

# Maximum file sizes (in bytes)
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB
MAX_PROFILE_PICTURE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_NOTE_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def sanitize_domain(domain: str) -> str:
    """
    Sanitize tenant domain to be safe for use in file paths
    
    Args:
        domain: Tenant domain string
        
    Returns:
        Sanitized domain string safe for file paths
    """
    if not domain:
        return "default"
    
    # Remove any invalid characters and replace with underscore
    sanitized = re.sub(r'[^a-z0-9_-]', '_', domain.lower())
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized if sanitized else "default"


def validate_file_type(file: UploadFile, allowed_types: set) -> None:
    """
    Validate that the uploaded file type is allowed
    
    Args:
        file: UploadFile object
        allowed_types: Set of allowed MIME types
        
    Raises:
        HTTPException if file type is not allowed
    """
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content type could not be determined"
        )
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' is not allowed. Allowed types: {', '.join(allowed_types)}"
        )


def validate_file_size(file: UploadFile, max_size: int) -> None:
    """
    Validate that the uploaded file size is within limits
    
    Args:
        file: UploadFile object
        max_size: Maximum file size in bytes
        
    Raises:
        HTTPException if file size exceeds limit
    """
    if file.size and file.size > max_size:
        size_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {size_mb}MB"
        )


def generate_filename(original_filename: str, tenant_domain: str, file_type: str = "file") -> str:
    """
    Generate a filename with tenant domain prefix
    
    Args:
        original_filename: Original filename from upload
        tenant_domain: Tenant domain to prefix
        file_type: Type of file (logo, profile_picture, etc.)
        
    Returns:
        Generated filename with tenant domain prefix
    """
    # Sanitize domain
    sanitized_domain = sanitize_domain(tenant_domain)
    
    # Get file extension
    file_ext = Path(original_filename).suffix.lower() if original_filename else '.jpg'
    
    # Generate unique filename: {domain}_{file_type}_{timestamp}_{uuid}{ext}
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    
    filename = f"{sanitized_domain}_{file_type}_{timestamp}_{unique_id}{file_ext}"
    
    return filename


async def save_uploaded_file(
    file: UploadFile,
    tenant_domain: str,
    file_category: str,
    subdirectory: Optional[str] = None,
    custom_filename: Optional[str] = None
) -> Tuple[str, str]:
    
    """
    Save an uploaded file with tenant domain prefix
    
    Args:
        file: UploadFile object
        tenant_domain: Tenant domain for prefixing
        file_category: Category of file (logo, profile_picture, etc.)
        subdirectory: Optional subdirectory within uploads folder (deprecated, use file_category)
        
    Returns:
        Tuple of (file_path, relative_path) where:
        - file_path: Absolute path to saved file
        - relative_path: Relative path from uploads directory (for database storage)
        
    Raises:
        HTTPException if file validation fails or save fails
    """
    # Determine the upload subdirectory based on file_category
    if file_category == 'logo':
        upload_subdir = 'logos'
    elif file_category == 'profile_picture':
        upload_subdir = 'profile_pictures'
    elif file_category == 'notes':
        upload_subdir = 'notes'
    else:
        # Use file_category as subdirectory name
        upload_subdir = file_category
    
    # Validate file type based on category
    if file_category == 'logo':
        validate_file_type(file, ALLOWED_LOGO_TYPES)
        validate_file_size(file, MAX_LOGO_SIZE)
    elif file_category == 'profile_picture':
        validate_file_type(file, ALLOWED_PROFILE_PICTURE_TYPES)
        validate_file_size(file, MAX_PROFILE_PICTURE_SIZE)
    elif file_category == 'notes':
        validate_file_type(file, ALLOWED_NOTE_FILE_TYPES)
        validate_file_size(file, MAX_NOTE_FILE_SIZE)
    else:
        # Default validation for other file types
        validate_file_type(file, ALLOWED_IMAGE_TYPES)
        validate_file_size(file, MAX_PROFILE_PICTURE_SIZE)
    
    # Generate filename - use custom filename if provided, otherwise generate one
    original_filename = file.filename or "uploaded_file"
    if custom_filename:
        # Sanitize custom filename for filesystem safety
        sanitized_custom = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', custom_filename)
        sanitized_custom = re.sub(r'_+', '_', sanitized_custom).strip('_')
        # Get file extension from original file
        file_ext = Path(original_filename).suffix.lower() if original_filename else ''
        # Combine sanitized custom name with extension
        filename = f"{sanitized_custom}{file_ext}"
    else:
        filename = generate_filename(original_filename, tenant_domain, file_category)
    
    # Determine upload directory structure: uploads/{subdirectory}/
    base_upload_dir = os.path.join(os.getcwd(), 'uploads')
    upload_dir = os.path.join(base_upload_dir, upload_subdir)
    
    # Create directory if it doesn't exist
    os.makedirs(upload_dir, exist_ok=True)
    
    # Full file path: {cwd}/uploads/{subdirectory}/{filename}
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    try:
        # Read file content
        content = await file.read()
        
        # Write to disk
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Generate relative path for database storage: {subdirectory}/{filename}
        # This will be used to construct URLs like /api/v1/uploads/{subdirectory}/{filename}
        relative_path = os.path.join(upload_subdir, filename).replace('\\', '/')
        
        return file_path, relative_path
        
    except Exception as e:
        # Clean up if file was partially written
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


def delete_file(file_path: str) -> bool:
    """
    Delete a file from the filesystem
    
    Args:
        file_path: Path to file (can be relative or absolute)
        
    Returns:
        True if file was deleted, False otherwise
    """
    try:
        # If relative path, make it absolute
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), 'uploads', file_path)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return False


def get_file_url(relative_path: str, base_url: str = "/api/v1/uploads", request: Optional[Request] = None) -> str:
    """
    Generate a URL for accessing an uploaded file
    
    Args:
        relative_path: Relative path from uploads directory
        base_url: Base URL for file access (default: "/api/v1/uploads")
        request: Optional FastAPI Request object to generate full URL
        
    Returns:
        Full URL to access the file (absolute URL if request provided, otherwise uses API_BASE_URL or current working directory)
    """
    import os
    from app.conf.config import get_settings
    
    # Normalize path separators
    normalized_path = relative_path.replace('\\', '/')
    
    # Remove leading slash from normalized_path if present
    if normalized_path.startswith('/'):
        normalized_path = normalized_path[1:]
        # print(f"Removed leading slash from relative_path. New path: {normalized_path}")
    
    # If request is provided, generate full URL from request
    if request:
        try:
            # Get the base URL from the request
            scheme = request.url.scheme
            host = request.url.hostname
            port = request.url.port
            
            # Construct base URL
            if port and port not in [80, 443]:
                server_base = f"{scheme}://{host}:{port}"
            else:
                server_base = f"{scheme}://{host}"
            
            return f"{server_base}{base_url}/{normalized_path}"
        except Exception as e:
            # Fallback if request parsing fails
            print(f"Warning: Could not generate full URL from request: {e}")
            pass
    
    # Try to get base URL from environment variable
    api_base_url = os.getenv("API_BASE_URL")
    if api_base_url:
        # Remove trailing slash if present
        api_base_url = api_base_url.rstrip('/')
        return f"{api_base_url}{base_url}/{normalized_path}"
    
    # Fallback: Use current working directory to construct URL
    # This assumes the server is running from the project root
    try:
        cwd = os.getcwd()
        # Extract server info from common patterns or use defaults
        # Default to localhost:8000 if no API_BASE_URL is set
        default_base = "http://localhost:8000"
        
        # Check if there's a port in environment
        port = os.getenv("PORT", "8000")
        host = os.getenv("HOST", "localhost")
        scheme = os.getenv("SCHEME", "http")
        
        # Construct base URL from environment or use default
        if os.getenv("API_BASE_URL"):
            server_base = os.getenv("API_BASE_URL").rstrip('/')
        else:
            server_base = f"{scheme}://{host}:{port}"
        
        return f"{server_base}{base_url}/{normalized_path}"
    except Exception as e:
        # Final fallback: return relative URL
        print(f"Warning: Could not generate full URL: {e}")
        return f"{base_url}/{normalized_path}"
