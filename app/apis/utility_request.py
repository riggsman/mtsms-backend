from sqlalchemy.orm import Session
from app.models.utility_request import UtilityRequest
from app.schemas.utility_request import UtilityRequestCreate, UtilityRequestUpdate, UtilityRequestResponse
from app.helpers.pagination import paginated_response
from typing import List, Optional
from datetime import datetime

def create_utility_request(db: Session, util_data: UtilityRequestCreate, institution_id: int, user_id: Optional[int] = None) -> UtilityRequest:
    utility = UtilityRequest(
        institution_id=institution_id,
        requested_by=user_id,
        utility_type=util_data.utility_type,
        location=util_data.location,
        description=util_data.description,
        status="pending"
    )
    db.add(utility)
    db.commit()
    db.refresh(utility)
    return utility

def get_utility_requests(db: Session, institution_id: int, status: Optional[str] = None, page: int = 1, page_size: int = 20):
    query = db.query(UtilityRequest).filter(UtilityRequest.institution_id == institution_id, UtilityRequest.deleted_at == None)
    if status:
        query = query.filter(UtilityRequest.status == status)
    return paginated_response(query, page, page_size, UtilityRequestResponse)

def get_utility_request_by_id(db: Session, util_id: int, institution_id: int) -> Optional[UtilityRequest]:
    return db.query(UtilityRequest).filter(
        UtilityRequest.id == util_id,
        UtilityRequest.institution_id == institution_id,
        UtilityRequest.deleted_at == None
    ).first()

def update_utility_request(db: Session, util_id: int, util_data: UtilityRequestUpdate, institution_id: int) -> Optional[UtilityRequest]:
    utility = get_utility_request_by_id(db, util_id, institution_id)
    if not utility:
        return None
    for key, value in util_data.dict(exclude_unset=True).items():
        setattr(utility, key, value)
    db.commit()
    db.refresh(utility)
    return utility

def approve_utility_request(db: Session, util_id: int, institution_id: int, handled_by: int) -> Optional[UtilityRequest]:
    utility = get_utility_request_by_id(db, util_id, institution_id)
    if not utility:
        return None
    utility.status = "approved"
    utility.handled_by = handled_by
    utility.handled_at = datetime.utcnow()
    db.commit()
    db.refresh(utility)
    return utility

def reject_utility_request(db: Session, util_id: int, institution_id: int, notes: str) -> Optional[UtilityRequest]:
    utility = get_utility_request_by_id(db, util_id, institution_id)
    if not utility:
        return None
    utility.status = "rejected"
    utility.notes = notes
    db.commit()
    db.refresh(utility)
    return utility

def complete_utility_request(db: Session, util_id: int, institution_id: int, notes: str) -> Optional[UtilityRequest]:
    utility = get_utility_request_by_id(db, util_id, institution_id)
    if not utility:
        return None
    utility.status = "completed"
    utility.notes = notes
    utility.handled_at = datetime.utcnow()
    db.commit()
    db.refresh(utility)
    return utility

def delete_utility_request(db: Session, util_id: int, institution_id: int):
    utility = get_utility_request_by_id(db, util_id, institution_id)
    if utility:
        utility.deleted_at = datetime.utcnow()
        db.commit()
    return utility

def get_pending_utility_count(db: Session, institution_id: int) -> int:
    return db.query(UtilityRequest).filter(
        UtilityRequest.institution_id == institution_id,
        UtilityRequest.status == "pending",
        UtilityRequest.deleted_at == None
    ).count()