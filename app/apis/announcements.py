from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.announcement import Announcement
from app.models.user import User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from app.exceptions import NotFoundError, ValidationError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity, get_user_display_name
import datetime

def get_announcements(
    db: Session,
    institution_id: int,
    skip: int = 0,
    limit: int = 100,
    user_role: Optional[str] = None
) -> tuple[List[Announcement], int]:
    """Get list of announcements for a specific institution with pagination, filtered by target audience"""
    query = db.query(Announcement).filter(
        Announcement.institution_id == institution_id,
        Announcement.deleted_at.is_(None)
    )
    
    # Filter by target audience based on user role
    if user_role:
        # Admin roles (admin, super_admin, secretary) can see ALL announcements
        if user_role in ["admin", "super_admin", "secretary"]:
            # No filtering - admins see everything
            pass
        # If user is a student, show only "students" or "all" announcements
        elif user_role == "student":
            query = query.filter(
                (Announcement.target_audience == "students") | 
                (Announcement.target_audience == "all")
            )
        # If user is staff, show only "staff" or "all" announcements
        elif user_role == "staff":
            query = query.filter(
                (Announcement.target_audience == "staff") | 
                (Announcement.target_audience == "all")
            )
    
    query = query.order_by(Announcement.created_at.desc())
    announcements, total = paginate_query(query, page=(skip // limit) + 1, page_size=limit)
    return announcements, total

def get_announcement(db: Session, announcement_id: int, institution_id: int) -> Announcement:
    """Get an announcement by ID (tenant-scoped)"""
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id,
        Announcement.institution_id == institution_id,
        Announcement.deleted_at.is_(None)
    ).first()
    if not announcement:
        raise NotFoundError(f"Announcement with ID {announcement_id} not found")
    return announcement

def create_announcement(
    db: Session,
    announcement: AnnouncementCreate,
    institution_id: int,
    current_user: User
) -> Announcement:
    """Create a new announcement for a specific institution"""
    if not institution_id:
        raise ValidationError("institution_id is required to create an announcement")
    
    new_announcement = Announcement(
        institution_id=institution_id,
        title=announcement.title,
        content=announcement.content,
        target_audience=announcement.target_audience or "all",
        created_by=current_user.id
    )
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    
    # Log activity
    try:
        log_create_activity(
            db=db,
            current_user=current_user,
            entity_type="announcement",
            entity_id=new_announcement.id,
            entity_name=announcement.title,
            institution_id=institution_id,
            content=f"Created announcement: {announcement.title}"
        )
    except Exception as e:
        print(f"Error logging announcement creation activity: {e}")
    
    return new_announcement

def update_announcement(
    db: Session,
    announcement_id: int,
    announcement_update: AnnouncementUpdate,
    institution_id: int,
    current_user: User
) -> Announcement:
    """Update an announcement (tenant-scoped)"""
    announcement = get_announcement(db, announcement_id, institution_id)
    
    update_data = announcement_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(announcement, field, value)
    
    db.commit()
    db.refresh(announcement)
    
    # Log activity
    try:
        log_update_activity(
            db=db,
            current_user=current_user,
            entity_type="announcement",
            entity_id=announcement.id,
            entity_name=announcement.title,
            institution_id=institution_id,
            content=f"Updated announcement: {announcement.title}"
        )
    except Exception as e:
        print(f"Error logging announcement update activity: {e}")
    
    return announcement

def delete_announcement(
    db: Session,
    announcement_id: int,
    institution_id: int,
    current_user: User
) -> bool:
    """Soft delete an announcement (tenant-scoped)"""
    announcement = get_announcement(db, announcement_id, institution_id)
    
    announcement.deleted_at = datetime.datetime.utcnow()
    db.commit()
    
    # Log activity
    try:
        log_delete_activity(
            db=db,
            current_user=current_user,
            entity_type="announcement",
            entity_id=announcement.id,
            entity_name=announcement.title,
            institution_id=institution_id,
            content=f"Deleted announcement: {announcement.title}"
        )
    except Exception as e:
        print(f"Error logging announcement deletion activity: {e}")
    
    return True
