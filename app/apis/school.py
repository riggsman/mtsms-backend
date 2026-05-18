"""
School API - CRUD operations for schools and school fees
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.school import School, SchoolFee
from app.models.academic_year import AcademicYear
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


def get_academic_year_name(db: Session, institution_id: int, academic_year_id: Optional[int]) -> Optional[str]:
    if not academic_year_id:
        return None
    row = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.id == academic_year_id,
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    return row.name if row else None


def _parse_date_string(value: Optional[str]):
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:19] if "T" in s else s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_academic_year_date_bounds(
    db: Session, institution_id: int, academic_year_id: Optional[int]
):
    """Return (start, end) datetimes for an academic year, or (None, None)."""
    if not academic_year_id:
        return None, None
    row = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.id == academic_year_id,
            AcademicYear.institution_id == institution_id,
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None, None
    start = _parse_date_string(row.start_date)
    end = _parse_date_string(row.end_date)
    if start:
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    if end:
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def get_current_academic_year_id(db: Session, institution_id: int) -> Optional[int]:
    row = (
        db.query(AcademicYear)
        .filter(
            AcademicYear.institution_id == institution_id,
            AcademicYear.is_current.is_(True),
            AcademicYear.deleted_at.is_(None),
        )
        .first()
    )
    return row.id if row else None


def school_fee_response(fee: SchoolFee, db: Session, institution_id: int) -> SchoolFeeResponse:
    ay_name = get_academic_year_name(db, institution_id, getattr(fee, "academic_year_id", None))
    return SchoolFeeResponse.from_model(fee, academic_year_name=ay_name)


def get_school_fees(
    db: Session,
    school_id: int,
    institution_id: int,
    level: str = None,
    academic_year_id: Optional[int] = None,
) -> List[SchoolFee]:
    """Get fees for a school, optionally filtered by fee level and academic year"""
    from app.database.schema_patches import ensure_schema_patches
    ensure_schema_patches(db.get_bind())

    get_school_by_id(db, school_id, institution_id)

    query = db.query(SchoolFee).filter(SchoolFee.school_id == school_id)
    if level:
        query = query.filter(SchoolFee.level == level.upper().strip())
    if academic_year_id is not None:
        query = query.filter(SchoolFee.academic_year_id == academic_year_id)

    return query.order_by(SchoolFee.level).all()


def get_school_fee_by_id(db: Session, fee_id: int, institution_id: int) -> SchoolFee:
    """Get a school fee by ID"""
    fee = db.query(SchoolFee).join(School).filter(
        SchoolFee.id == fee_id,
        School.institution_id == institution_id
    ).first()
    
    if not fee:
        raise NotFoundError(f"School fee with ID {fee_id} not found")
    return fee


def get_school_fee_by_level(
    db: Session,
    school_id: int,
    level: str,
    institution_id: int,
    academic_year_id: Optional[int] = None,
) -> Optional[SchoolFee]:
    """Get fee for school + level, preferring the requested academic year then current then legacy default."""
    get_school_by_id(db, school_id, institution_id)
    level_norm = level.upper().strip()
    base = db.query(SchoolFee).filter(
        SchoolFee.school_id == school_id,
        SchoolFee.level == level_norm,
    )

    ids_to_try: List[int] = []
    if academic_year_id:
        ids_to_try.append(int(academic_year_id))
    else:
        current_id = get_current_academic_year_id(db, institution_id)
        if current_id:
            ids_to_try.append(current_id)

    for aid in ids_to_try:
        fee = base.filter(SchoolFee.academic_year_id == aid).first()
        if fee:
            return fee

    return base.filter(SchoolFee.academic_year_id.is_(None)).first()


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
    
    academic_year_id = getattr(fee_data, "academic_year_id", None)
    query = db.query(SchoolFee).filter(
        SchoolFee.school_id == school_id,
        SchoolFee.level == level,
    )
    if academic_year_id is not None:
        query = query.filter(SchoolFee.academic_year_id == academic_year_id)
    else:
        query = query.filter(SchoolFee.academic_year_id.is_(None))
    existing = query.first()

    if existing:
        existing.fee_amount = fee_data.fee_amount
        existing.fee_deadline = deadline
        if academic_year_id is not None:
            existing.academic_year_id = academic_year_id
        db.commit()
        db.refresh(existing)
        return existing
    else:
        fee = SchoolFee(
            school_id=school_id,
            level=level,
            academic_year_id=academic_year_id,
            fee_amount=fee_data.fee_amount,
            fee_deadline=deadline,
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
        fees = get_school_fees(db, school.id, institution_id)
        school_dict = {
            "id": school.id,
            "institution_id": school.institution_id,
            "name": school.name,
            "code": school.code,
            "description": school.description,
            "is_active": school.is_active,
            "sort_order": school.sort_order,
            "fees": [school_fee_response(f, db, institution_id) for f in fees],
            "created_at": school.created_at,
            "updated_at": school.updated_at,
        }
        result.append(school_dict)

    return result
