from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.specialty import Specialization
from app.models.department import Department
from app.models.user import User
from app.schemas.specializations import SpecializationRequest, SpecializationResponse, SpecializationUpdate
from app.exceptions import NotFoundError, ConflictError
from app.helpers.pagination import paginate_query
from app.helpers.activity_logger import log_create_activity, log_update_activity, log_delete_activity


def create_specialization(db: Session, specialization: SpecializationRequest, institution_id: Optional[int] = None, current_user: Optional[User] = None) -> Specialization:
    """Create a new specialization"""
    if not specialization.department_id:
        from app.exceptions import ValidationError
        raise ValidationError("department_id is required")
    
    department = db.query(Department).filter(
        Department.id == specialization.department_id,
        Department.deleted_at.is_(None)
    ).first()
    
    if not department:
        from app.exceptions import NotFoundError
        raise NotFoundError("Department not found")
    
    final_institution_id = specialization.institution_id or institution_id
    
    if not final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("institution_id is required. Either provide it in the request body or pass it as a parameter")
    
    if department.institution_id != final_institution_id:
        from app.exceptions import ValidationError
        raise ValidationError("Department must belong to your institution")
    
    existing = db.query(Specialization).filter(
        Specialization.code == specialization.code,
        Specialization.institution_id == final_institution_id,
        Specialization.deleted_at.is_(None)
    ).first()
    if existing:
        raise ConflictError(f"Specialization with code {specialization.code} already exists for this institution")
    
    specialization_dict = specialization.dict(exclude={'institution_id'})
    specialization_dict['institution_id'] = final_institution_id
    new_specialization = Specialization(**specialization_dict)
    db.add(new_specialization)
    db.commit()
    db.refresh(new_specialization)
    
    if current_user:
        try:
            spec_name = f"{specialization.code} - {specialization.name}"
            log_create_activity(
                db=db,
                current_user=current_user,
                entity_type="specialization",
                entity_id=new_specialization.id,
                entity_name=spec_name,
                institution_id=final_institution_id,
                content=f"Created specialization: {spec_name}"
            )
        except Exception as e:
            print(f"Error logging specialization creation activity: {e}")
    
    return new_specialization


def get_specialization(db: Session, specialization_id: int) -> Specialization:
    """Get a specialization by ID"""
    specialization = db.query(Specialization).filter(
        Specialization.id == specialization_id,
        Specialization.deleted_at.is_(None)
    ).first()
    if not specialization:
        raise NotFoundError(f"Specialization with ID {specialization_id} not found")
    return specialization


def get_specializations(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    institution_id: Optional[int] = None,
    department_id: Optional[int] = None
) -> tuple[List[Specialization], int]:
    """Get list of specializations with pagination"""
    query = db.query(Specialization).filter(Specialization.deleted_at.is_(None))
    
    if institution_id is not None:
        query = query.filter(Specialization.institution_id == institution_id)
    
    if department_id is not None:
        query = query.filter(Specialization.department_id == department_id)
    
    return paginate_query(query, page=(skip // limit) + 1, page_size=limit)


def update_specialization(db: Session, specialization_id: int, specialization_update: SpecializationUpdate, current_user: Optional[User] = None) -> Specialization:
    """Update a specialization"""
    specialization = get_specialization(db, specialization_id)
    
    update_data = specialization_update.dict(exclude_unset=True)
    
    if "code" in update_data:
        existing = db.query(Specialization).filter(
            Specialization.code == update_data["code"],
            Specialization.institution_id == specialization.institution_id,
            Specialization.id != specialization_id,
            Specialization.deleted_at.is_(None)
        ).first()
        if existing:
            raise ConflictError(f"Specialization with code {update_data['code']} already exists for this institution")
    
    for field, value in update_data.items():
        setattr(specialization, field, value)
    
    db.commit()
    db.refresh(specialization)
    
    if current_user:
        try:
            spec_name = f"{specialization.code} - {specialization.name}"
            log_update_activity(
                db=db,
                current_user=current_user,
                entity_type="specialization",
                entity_id=specialization_id,
                entity_name=spec_name,
                institution_id=specialization.institution_id,
                content=f"Updated specialization: {spec_name}"
            )
        except Exception as e:
            print(f"Error logging specialization update activity: {e}")
    
    return specialization


def delete_specialization(db: Session, specialization_id: int, current_user: Optional[User] = None) -> bool:
    """Soft delete a specialization"""
    specialization = get_specialization(db, specialization_id)
    spec_name = f"{specialization.code} - {specialization.name}"
    institution_id = specialization.institution_id
    
    from datetime import datetime
    specialization.deleted_at = datetime.utcnow()
    db.commit()
    
    if current_user:
        try:
            log_delete_activity(
                db=db,
                current_user=current_user,
                entity_type="specialization",
                entity_id=specialization_id,
                entity_name=spec_name,
                institution_id=institution_id,
                content=f"Deleted specialization: {spec_name}"
            )
        except Exception as e:
            print(f"Error logging specialization deletion activity: {e}")
    
    return True
