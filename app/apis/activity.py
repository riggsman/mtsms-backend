from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.activity import Activity
from app.schemas.activity import ActivityRequest
from app.helpers.pagination import paginate_query
from datetime import datetime

def create_activity(db: Session, activity: ActivityRequest) -> Activity:
    """Create a new activity log entry"""
    new_activity = Activity(
        institution_id=activity.institution_id,
        action=activity.action,
        entity_type=activity.entity_type,
        entity_id=activity.entity_id,
        performed_by=activity.performed_by,
        performer_role=activity.performer_role,
        performer_id=activity.performer_id,
        content=activity.content
    )
    db.add(new_activity)
    db.commit()
    db.refresh(new_activity)
    return new_activity

def get_activities(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    institution_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None
) -> tuple[List[Activity], int]:
    """Get list of activities with pagination and optional filters"""
    query = db.query(Activity)
    
    if institution_id:
        query = query.filter(Activity.institution_id == institution_id)
    if entity_type:
        query = query.filter(Activity.entity_type == entity_type)
    if action:
        query = query.filter(Activity.action.ilike(f"%{action}%"))
    
    # Order by most recent first
    query = query.order_by(Activity.created_at.desc())
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)

def log_activity(
    db: Session,
    institution_id: int,
    action: str,
    entity_type: str,
    performed_by: str,
    performer_role: str,
    entity_id: Optional[int] = None,
    performer_id: Optional[int] = None,
    content: Optional[str] = None
) -> Activity:
    """Helper function to log an activity"""
    activity_request = ActivityRequest(
        institution_id=institution_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        performed_by=performed_by,
        performer_role=performer_role,
        performer_id=performer_id,
        content=content
    )
    return create_activity(db, activity_request)
