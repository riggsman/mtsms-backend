from sqlalchemy.orm import Session
from typing import List, Optional
import json
from app.models.complaint import Complaint
from app.schemas.complaints import ComplaintRequest, ComplaintUpdate
from app.exceptions import NotFoundError
from app.helpers.pagination import paginate_query
from datetime import datetime

def create_complaint(db: Session, complaint: ComplaintRequest) -> Complaint:
    """Create a new complaint"""
    screenshots_json = json.dumps(complaint.screenshots) if complaint.screenshots else None
    
    new_complaint = Complaint(
        student_id=complaint.student_id,
        complaint_type=complaint.complaint_type,
        caption=complaint.caption,
        contents=complaint.contents,
        is_anonymous=complaint.is_anonymous,
        screenshots=screenshots_json,
        status="pending"
    )
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return new_complaint

def get_complaint(db: Session, complaint_id: int) -> Complaint:
    """Get a complaint by ID"""
    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id,
        Complaint.deleted_at.is_(None)
    ).first()
    if not complaint:
        raise NotFoundError(f"Complaint with ID {complaint_id} not found")
    # Parse screenshots JSON if exists
    if complaint.screenshots:
        try:
            complaint.screenshots = json.loads(complaint.screenshots)
        except:
            complaint.screenshots = []
    return complaint

def get_complaints(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    student_id: Optional[str] = None,
    complaint_type: Optional[str] = None,
    status: Optional[str] = None
) -> tuple[List[Complaint], int]:
    """Get list of complaints with pagination"""
    query = db.query(Complaint).filter(Complaint.deleted_at.is_(None))
    
    if student_id:
        query = query.filter(Complaint.student_id == student_id)
    
    if complaint_type:
        query = query.filter(Complaint.complaint_type == complaint_type)
    
    if status:
        query = query.filter(Complaint.status == status)
    
    complaints, total = paginate_query(query, page=(skip // limit) + 1, page_size=limit)
    
    # Parse screenshots JSON for each complaint
    for complaint in complaints:
        if complaint.screenshots:
            try:
                complaint.screenshots = json.loads(complaint.screenshots)
            except:
                complaint.screenshots = []
    
    return complaints, total

def update_complaint(db: Session, complaint_id: int, complaint_update: ComplaintUpdate) -> Complaint:
    """Update a complaint (typically to mark as addressed)"""
    complaint = get_complaint(db, complaint_id)
    
    update_data = complaint_update.dict(exclude_unset=True)
    
    # If status is being set to "addressed", set resolved_date
    if update_data.get('status') == 'addressed' and not complaint.resolved_date:
        update_data['resolved_date'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(complaint, field, value)
    
    db.commit()
    db.refresh(complaint)
    return complaint

def delete_complaint(db: Session, complaint_id: int) -> bool:
    """Soft delete a complaint"""
    complaint = get_complaint(db, complaint_id)
    complaint.deleted_at = datetime.utcnow()
    db.commit()
    return True

def get_student_complaints(db: Session, student_id: str) -> List[Complaint]:
    """Get all complaints for a specific student"""
    complaints = db.query(Complaint).filter(
        Complaint.student_id == student_id,
        Complaint.deleted_at.is_(None)
    ).all()
    # Parse screenshots JSON for each complaint
    for complaint in complaints:
        if complaint.screenshots:
            try:
                complaint.screenshots = json.loads(complaint.screenshots)
            except:
                complaint.screenshots = []
    return complaints