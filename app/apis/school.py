"""
School API - CRUD operations for schools and school fees
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.school import School, SchoolFee
from app.schemas.school import (
    SchoolCreate,
    SchoolUpdate,
    SchoolFeeCreate,
    SchoolFeeUpdate,
    SchoolFeeResponse
)
from app.exceptions import NotFoundError, ValidationError


# ============================================
# School CRUD
# ============================================

def get_schools(db: Session, institution_id: int, include_inactive: bool = False) -> List[School]:
    """Get all schools for an institution"""
    query = db.query(School).filter(School.institution_id == institution_id)
    if not include_inactive:
        query = query.filter(School.is_active == True)
    return query.order_by(School.sort_order, School.name).all()


def get_school_by_id(db: Session, school_id: int, institution_id: int) -> School:
    """Get a school by ID"""
    school = db.query(School).filter(
        School.id == school_id,
        School.institution_id == institution_id
    ).first()
    if not school:
        raise NotFoundError(f"School with ID {school_id} not found")
    return school


def create_school(db: Session, institution_id: int, school_data: SchoolCreate) -> School:
    """Create a new school"""
    school = School(
        institution_id=institution_id,
        name=school_data.name.strip(),
        code=(school_data.code or "").strip() or None,
        description=school_data.description,
        is_active=school_data.is_active,
        sort_order=school_data.sort_order
    )
    db.add(school)
    db.commit()
    db.refresh(school)
    return school


def update_school(db: Session, school_id: int, institution_id: int, school_data: SchoolUpdate) -> School:
    """Update a school"""
    school = get_school_by_id(db, school_id, institution_id)
    
    data = school_data.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "name" and v is not None:
            setattr(school, k, str(v).strip())
        elif k == "code" and v is not None:
            setattr(school, k, str(v).strip() or None)
        else:
            setattr(school, k, v)
    
    db.commit()
    db.refresh(school)
    return school


def delete_school(db: Session, school_id: int, institution_id: int) -> bool:
    """Delete a school (cascade deletes fees)"""
    school = get_school_by_id(db, school_id, institution_id)
    db.delete(school)
    db.commit()
    return True


# ============================================
# School Fee CRUD
# ============================================

VALID_LEVELS = ["HND", "DEGREE", "MASTERS"]


def get_school_fees(db: Session, school_id: int, institution_id: int, level: str = None) -> List[SchoolFee]:
    """Get fees for a school, optionally filtered by fee level"""
    # Verify school access
    get_school_by_id(db, school_id, institution_id)
    
    query = db.query(SchoolFee).filter(SchoolFee.school_id == school_id)
    if level:
        query = query.filter(SchoolFee.level == level.upper().strip())
    
    fees = query.order_by(SchoolFee.level).all()
    return fees


def get_school_fee_by_id(db: Session, fee_id: int, institution_id: int) -> SchoolFee:
    """Get a school fee by ID"""
    fee = db.query(SchoolFee).join(School).filter(
        SchoolFee.id == fee_id,
        School.institution_id == institution_id
    ).first()
    
    if not fee:
        raise NotFoundError(f"School fee with ID {fee_id} not found")
    return fee


def get_school_fee_by_level(db: Session, school_id: int, level: str, institution_id: int) -> Optional[SchoolFee]:
    """Get fee for a specific school + level combination"""
    # Verify school access
    get_school_by_id(db, school_id, institution_id)
    
    fee = db.query(SchoolFee).filter(
        SchoolFee.school_id == school_id,
        SchoolFee.level == level.upper()
    ).first()
    
    return fee


def create_or_update_school_fee(
    db: Session,
    school_id: int,
    institution_id: int,
    fee_data: SchoolFeeCreate
) -> SchoolFee:
    """Create or update a school fee (upsert by school_id + level)"""
    # Validate level
    level = fee_data.level.upper()
    if level not in VALID_LEVELS:
        raise ValidationError(f"Level must be one of: {', '.join(VALID_LEVELS)}")
    
    # Verify school access
    get_school_by_id(db, school_id, institution_id)
    
    # Parse deadline
    deadline = None
    if fee_data.fee_deadline:
        try:
            deadline = datetime.fromisoformat(fee_data.fee_deadline.replace('Z', '+00:00'))
        except ValueError:
            try:
                deadline = datetime.strptime(fee_data.fee_deadline, '%Y-%m-%d')
            except ValueError:
                raise ValidationError("Invalid fee_deadline format. Use YYYY-MM-DD")
    
    # Check if fee already exists for this school + level
    existing = get_school_fee_by_level(db, school_id, level, institution_id)
    
    if existing:
        # Update existing
        existing.fee_amount = fee_data.fee_amount
        existing.fee_deadline = deadline
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        fee = SchoolFee(
            school_id=school_id,
            level=level,
            fee_amount=fee_data.fee_amount,
            fee_deadline=deadline
        )
        db.add(fee)
        db.commit()
        db.refresh(fee)
        return fee


def update_school_fee(
    db: Session,
    fee_id: int,
    institution_id: int,
    fee_data: SchoolFeeUpdate
) -> SchoolFee:
    """Update a school fee"""
    fee = get_school_fee_by_id(db, fee_id, institution_id)
    
    if fee_data.fee_amount is not None:
        fee.fee_amount = fee_data.fee_amount
    
    if fee_data.fee_deadline is not None:
        try:
            fee.fee_deadline = datetime.fromisoformat(fee_data.fee_deadline.replace('Z', '+00:00'))
        except ValueError:
            try:
                fee.fee_deadline = datetime.strptime(fee_data.fee_deadline, '%Y-%m-%d')
            except ValueError:
                raise ValidationError("Invalid fee_deadline format. Use YYYY-MM-DD")
    
    db.commit()
    db.refresh(fee)
    return fee


def delete_school_fee(db: Session, fee_id: int, institution_id: int) -> bool:
    """Delete a school fee"""
    fee = get_school_fee_by_id(db, fee_id, institution_id)
    db.delete(fee)
    db.commit()
    return True


def get_all_schools_with_fees(db: Session, institution_id: int) -> List[dict]:
    """Get all schools with their fees for an institution"""
    schools = get_schools(db, institution_id)
    result = []
    
    for school in schools:
        school_dict = {
            "id": school.id,
            "institution_id": school.institution_id,
            "name": school.name,
            "code": school.code,
            "description": school.description,
            "is_active": school.is_active,
            "sort_order": school.sort_order,
            "fees": [SchoolFeeResponse.from_model(f) for f in school.fees],
            "created_at": school.created_at,
            "updated_at": school.updated_at
        }
        result.append(school_dict)
    
    return result
