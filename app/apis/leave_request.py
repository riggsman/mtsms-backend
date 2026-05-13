from sqlalchemy.orm import Session
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestResponse
from app.helpers.pagination import paginated_response
from typing import List, Optional
from datetime import datetime

def create_leave_request(db: Session, leave_data: LeaveRequestCreate, institution_id: int, user_id: int) -> LeaveRequest:
    leave = LeaveRequest(
        institution_id=institution_id,
        staff_id=user_id,
        leave_type=leave_data.leave_type,
        start_date=leave_data.start_date,
        end_date=leave_data.end_date,
        reason=leave_data.reason,
        status="pending"
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return leave

def get_leave_requests(db: Session, institution_id: int, status: Optional[str] = None, page: int = 1, page_size: int = 20):
    query = db.query(LeaveRequest).filter(LeaveRequest.institution_id == institution_id, LeaveRequest.deleted_at == None)
    if status:
        query = query.filter(LeaveRequest.status == status)
    return paginated_response(query, page, page_size, LeaveRequestResponse)

def get_leave_request_by_id(db: Session, leave_id: int, institution_id: int) -> Optional[LeaveRequest]:
    return db.query(LeaveRequest).filter(
        LeaveRequest.id == leave_id,
        LeaveRequest.institution_id == institution_id,
        LeaveRequest.deleted_at == None
    ).first()

def update_leave_request(db: Session, leave_id: int, leave_data: LeaveRequestUpdate, institution_id: int) -> Optional[LeaveRequest]:
    leave = get_leave_request_by_id(db, leave_id, institution_id)
    if not leave:
        return None
    for key, value in leave_data.dict(exclude_unset=True).items():
        setattr(leave, key, value)
    db.commit()
    db.refresh(leave)
    return leave

def approve_leave_request(db: Session, leave_id: int, institution_id: int, approved_by: int) -> Optional[LeaveRequest]:
    leave = get_leave_request_by_id(db, leave_id, institution_id)
    if not leave:
        return None
    leave.status = "approved"
    leave.approved_by = approved_by
    leave.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(leave)
    return leave

def reject_leave_request(db: Session, leave_id: int, institution_id: int, reason: str) -> Optional[LeaveRequest]:
    leave = get_leave_request_by_id(db, leave_id, institution_id)
    if not leave:
        return None
    leave.status = "rejected"
    leave.rejection_reason = reason
    db.commit()
    db.refresh(leave)
    return leave

def delete_leave_request(db: Session, leave_id: int, institution_id: int):
    leave = get_leave_request_by_id(db, leave_id, institution_id)
    if leave:
        leave.deleted_at = datetime.utcnow()
        db.commit()
    return leave

def get_pending_leave_count(db: Session, institution_id: int) -> int:
    return db.query(LeaveRequest).filter(
        LeaveRequest.institution_id == institution_id,
        LeaveRequest.status == "pending",
        LeaveRequest.deleted_at == None
    ).count()