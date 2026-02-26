"""
Helper module for logging activities across the application.
This module provides a convenient way to log CRUD operations.
"""
from sqlalchemy.orm import Session
from app.apis.activity import log_activity
from app.models.user import User
from typing import Optional

def get_user_display_name(user: User) -> str:
    """Get display name for a user"""
    if user.firstname and user.lastname:
        return f"{user.firstname} {user.lastname}".strip()
    elif user.username:
        return user.username
    elif user.email:
        return user.email.split('@')[0]
    else:
        return "Unknown User"

def log_create_activity(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    institution_id: Optional[int] = None,
    content: Optional[str] = None
):
    """Log a create activity"""
    institution_id = institution_id or current_user.institution_id
    if not institution_id:
        return  # Skip logging if no institution_id
    
    action = f"{entity_type.capitalize()} Created"
    # Use provided content, or generate default content
    if content is None:
        content = f"Created {entity_type}: {entity_name}" if entity_name else None
    
    log_activity(
        db=db,
        institution_id=institution_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by=get_user_display_name(current_user),
        performer_role=current_user.role or "Unknown",
        performer_id=current_user.id,
        content=content
    )

def log_update_activity(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    institution_id: Optional[int] = None,
    content: Optional[str] = None
):
    """Log an update activity"""
    institution_id = institution_id or current_user.institution_id
    if not institution_id:
        return  # Skip logging if no institution_id
    
    action = f"{entity_type.capitalize()} Updated"
    # Use provided content, or generate default content
    if content is None:
        content = f"Updated {entity_type}: {entity_name}" if entity_name else None
    
    log_activity(
        db=db,
        institution_id=institution_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by=get_user_display_name(current_user),
        performer_role=current_user.role or "Unknown",
        performer_id=current_user.id,
        content=content
    )

def log_delete_activity(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    institution_id: Optional[int] = None,
    content: Optional[str] = None
):
    """Log a delete activity"""
    institution_id = institution_id or current_user.institution_id
    if not institution_id:
        return  # Skip logging if no institution_id
    
    action = f"{entity_type.capitalize()} Deleted"
    # Use provided content, or generate default content
    if content is None:
        content = f"Deleted {entity_type}: {entity_name}" if entity_name else None
    
    log_activity(
        db=db,
        institution_id=institution_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by=get_user_display_name(current_user),
        performer_role=current_user.role or "Unknown",
        performer_id=current_user.id,
        content=content
    )
